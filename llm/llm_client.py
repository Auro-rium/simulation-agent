import os
import json
import logging
import hashlib
import asyncio
from typing import Any, Dict, Optional, List, Union
from groq import AsyncGroq, GroqError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("llm_client")

# --- Groq Constants ---
MODEL_REASONING = "llama-3.3-70b-versatile" # High Intelligence
MODEL_FAST = "llama-3.1-8b-instant"         # High Speed

# Strict Token Budgets
FLASH_MAX_OUTPUT = 1024
PRO_MAX_OUTPUT = 4096

class LLMClient:
    """
    Groq-Based Production LLM Client (v0.4.1).
    Removed all Gemini legacy code.
    """
    MODEL_REASONING = MODEL_REASONING
    MODEL_FAST = MODEL_FAST

    def __init__(self, project_id: Optional[str] = None, location: Optional[str] = None):
        """Analyze environment for Groq."""
        self.api_key = os.environ.get("GROQ_API_KEY")
        
        if not self.api_key:
             logger.warning("GROQ_API_KEY not found.")
             
        self.client = AsyncGroq(api_key=self.api_key)
        
        # Cache setup
        self.cache_dir = os.path.join(os.getcwd(), "cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_key(self, prompt: str, model: str, params: Dict) -> str:
        blob = json.dumps({"prompt": prompt, "model": model, "params": params}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    async def _read_cache(self, key: str) -> Optional[Dict]:
        path = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(path):
            try:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, self._read_json_file, path)
            except Exception:
                return None
        return None

    def _read_json_file(self, path: str) -> Dict:
        with open(path, "r") as f:
            return json.load(f)

    async def _write_cache(self, key: str, data: Dict):
        path = os.path.join(self.cache_dir, f"{key}.json")
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._write_json_file, path, data)
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")

    def _write_json_file(self, path: str, data: Dict):
        tmp_path = path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, path)

    async def generate(self, 
                     prompt: str, 
                     model: str = MODEL_FAST, 
                     *, 
                     max_tokens: int = None, 
                     temperature: float = 0.7, 
                     seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Groq Generation Logic.
        """
        # Alias handling for user convenience (if needed), otherwise strict
        if model == "gptss120b": model = MODEL_REASONING
        
        # Enforce Token Limits based on "Flash" (8b) or "Pro" (70b) lineage
        if "8b" in model:
             limit = FLASH_MAX_OUTPUT
        else:
             limit = PRO_MAX_OUTPUT
             
        if max_tokens:
            max_tokens = min(max_tokens, limit)
        else:
            max_tokens = limit

        params = {"max_tokens": max_tokens, "temperature": temperature, "seed": seed}
        cache_key = self._get_cache_key(prompt, model, params)
        
        # Check cache
        cached = await self._read_cache(cache_key)
        if cached:
            cached["meta"]["cached"] = True
            return cached

        try:
            # Groq API Call
            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_completion_tokens": max_tokens,
                "stream": False
            }
            if seed is not None:
                kwargs["seed"] = seed
                
            response = await self.client.chat.completions.create(**kwargs)
            
            # Finish Reason Handling
            choice = response.choices[0]
            finish_reason = choice.finish_reason
            text_content = choice.message.content
            
            meta = {
                "model": model,
                "finish_reason": finish_reason,
                "cached": False,
                "degraded": False,
                "seed": seed
            }
            
            if finish_reason == "length":
                meta["degraded"] = True
                meta["warning"] = "Max tokens reached."
            
            result = {
                "text": text_content,
                "meta": meta
            }
            
            await self._write_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Groq Generate Error: {e}")
            raise e

    async def generate_with_retries(self, 
                                  prompt: str, 
                                  model: str = MODEL_FAST, 
                                  retries: int = 2,
                                  timeout: float = 60.0,
                                  **kwargs) -> Dict[str, Any]:
        """
        Retries on API/Network errors.
        """
        last_exception = None
        for attempt in range(retries + 1):
            try:
                result = await asyncio.wait_for(
                    self.generate(prompt, model=model, **kwargs),
                    timeout=timeout
                )
                return result

            except (asyncio.TimeoutError, GroqError) as e:
                last_exception = e
                logger.warning(f"Error on {model} (Attempt {attempt+1}): {e}")
            except Exception as e:
                last_exception = e
                logger.warning(f"Unexpected error on {model} (Attempt {attempt+1}): {e}")
                
            if attempt < retries:
                 await asyncio.sleep(2 ** attempt)

        raise last_exception or RuntimeError("All retries failed")

    async def generate_structured_output(self, 
                                       prompt: str, 
                                       response_schema: Dict[str, Any],
                                       model: str = MODEL_REASONING, 
                                       **kwargs) -> Dict[str, Any]:
        """
        Generates JSON using Groq's JSON mode.
        """
        # Auto-upgrade purely 8b models if we suspect they might struggle, 
        # but User asked for strict Llama usage. 
        # Llama 3.1 8b is okay at JSON but 70b is better.
        # We'll default to 70b (MODEL_REASONING) but allow override.
        
        full_prompt = (
            f"{prompt}\n\n"
            f"IMPORTANT: Respond with VALID JSON only. matching this schema:\n"
            f"{json.dumps(response_schema, indent=2)}"
        )
        
        try:
             response = await self.client.chat.completions.create(
                 model=model,
                 messages=[
                     {"role": "system", "content": f"You are a structured data assistant. Output JSON matching: {json.dumps(response_schema)}"},
                     {"role": "user", "content": prompt}
                 ],
                 temperature=0.1,
                 response_format={"type": "json_object"},
                 stream=False
             )
             text_response = response.choices[0].message.content
             return json.loads(text_response)
             
        except Exception as e:
             logger.error(f"Groq JSON Error: {e}")
             raise ValueError(f"Failed to generate JSON: {e}")

    # Compatibility
    def generate_text(self, prompt: str, model_type: str = "reasoning", temperature: float = 0.7) -> str:
        """DEPRECATED: Sync wrapper."""
        model = MODEL_REASONING if model_type == "reasoning" else MODEL_FAST
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
             import concurrent.futures
             pool = concurrent.futures.ThreadPoolExecutor()
             future = pool.submit(lambda: asyncio.run(self.generate(prompt, model=model, temperature=temperature)))
             result = future.result()
             return result["text"]

        return loop.run_until_complete(
            self.generate(prompt, model=model, temperature=temperature)
        )["text"]
