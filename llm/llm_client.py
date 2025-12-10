import os
import json
import logging
import hashlib
import asyncio
from typing import Any, Dict, Optional, List, Union
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content, SafetySetting, HarmCategory, HarmBlockThreshold, GenerationConfig
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger("llm_client")

class LLMClient:
    """Wrapper for Vertex AI Gemini models with async, caching, and retry support."""

    def __init__(self, project_id: Optional[str] = None, location: Optional[str] = None):
        """Initialize Vertex AI client."""
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.environ.get("VERTEX_AI_LOCATION")
        
        # Check for legacy/alternative auth variable
        api_key = os.environ.get("GOOGLE_API_KEY")
        
        if not self.project_id:
            logger.warning("GOOGLE_CLOUD_PROJECT not set.")
            if api_key:
                logger.warning("Found GOOGLE_API_KEY. Note that Vertex AI SDK normally uses ADC.")
        
        if not self.project_id or not self.location:
             if api_key and not self.project_id:
                 raise ValueError("GOOGLE_CLOUD_PROJECT env var is missing.")
             raise ValueError("GOOGLE_CLOUD_PROJECT and VERTEX_AI_LOCATION must be set.")
            
        try:
            vertexai.init(project=self.project_id, location=self.location)
        except Exception as e:
            print(f"Failed to initialize Vertex AI: {e}")
            raise

        self.models = {
            "gemini-2.5-pro": GenerativeModel("gemini-2.5-pro"),
            "gemini-2.5-flash": GenerativeModel("gemini-2.5-flash")
        }
        
        # Cache setup
        self.cache_dir = os.path.join(os.getcwd(), "cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_model(self, model_name: str) -> GenerativeModel:
        if model_name not in self.models:
             # Fallback or lazy load
             self.models[model_name] = GenerativeModel(model_name)
        return self.models[model_name]

    def _get_cache_key(self, prompt: str, model: str, params: Dict) -> str:
        blob = json.dumps({"prompt": prompt, "model": model, "params": params}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    async def _read_cache(self, key: str) -> Optional[Dict]:
        path = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(path):
            try:
                # Run file IO in thread
                return await asyncio.to_thread(self._read_json_file, path)
            except Exception:
                return None
        return None

    def _read_json_file(self, path: str) -> Dict:
        with open(path, "r") as f:
            return json.load(f)

    async def _write_cache(self, key: str, data: Dict):
        path = os.path.join(self.cache_dir, f"{key}.json")
        tmp_path = path + ".tmp"
        try:
            await asyncio.to_thread(self._write_json_file, tmp_path, path, data)
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")

    def _write_json_file(self, tmp_path: str, final_path: str, data: Dict):
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, final_path)

    async def generate(self, 
                     prompt: str, 
                     model: str = "gemini-2.5-flash", 
                     *, 
                     max_tokens: int = 8192, 
                     temperature: float = 0.7, 
                     seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Async generation with caching and retries.
        Returns dict: {"text": str, "meta": dict}
        """
        params = {"max_tokens": max_tokens, "temperature": temperature, "seed": seed}
        cache_key = self._get_cache_key(prompt, model, params)
        
        # Check cache
        cached = await self._read_cache(cache_key)
        if cached:
            cached["meta"]["cached"] = True
            return cached

        # Generation Config
        config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            candidate_count=1,
            seed=seed
        )
        
        # Safety Settings
        safety_settings = [
            SafetySetting(
                category=category,
                threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH
            ) for category in [
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                HarmCategory.HARM_CATEGORY_HARASSMENT,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT
            ]
        ]
        
        gen_model = self._get_model(model)
        
        try:
            # Native async call
            response = await gen_model.generate_content_async(
                prompt,
                generation_config=config,
                safety_settings=safety_settings
            )
            
            text_content = response.text if response.text else ""
            result = {
                "text": text_content,
                "meta": {
                    "model": model,
                    "cached": False,
                    "finish_reason": str(response.candidates[0].finish_reason) if response.candidates else "UNKNOWN"
                }
            }
            
            # Write cache
            await self._write_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"LLM Generate Error: {e}")
            raise

    async def generate_with_retries(self, 
                                  prompt: str, 
                                  model: str = "gemini-2.5-flash", 
                                  retries: int = 2,
                                  timeout: float = 60.0,
                                  **kwargs) -> Dict[str, Any]:
        """Wrapper for generate with timeout and exponential backoff."""
        last_exception = None
        for attempt in range(retries + 1):
            try:
                return await asyncio.wait_for(
                    self.generate(prompt, model=model, **kwargs),
                    timeout=timeout
                )
            except (asyncio.TimeoutError, Exception) as e:
                last_exception = e
                logger.warning(f"Attempt {attempt+1} failed for {model}: {e}")
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt) # 1s, 2s, 4s...
        
        raise last_exception or RuntimeError("All retries failed")

    async def generate_structured_output(self, 
                                       prompt: str, 
                                       response_schema: Dict[str, Any],
                                       model: str = "gemini-2.5-flash",
                                       **kwargs) -> Dict[str, Any]:
        """Generates JSON output matching a schema (async)."""
        full_prompt = (
            f"{prompt}\n\n"
            f"IMPORTANT: Respond with VALID JSON only. matching this schema:\n"
            f"{json.dumps(response_schema, indent=2)}"
        )
        
        # Force low temperature for structure
        kwargs["temperature"] = 0.1
        
        result_dict = await self.generate_with_retries(full_prompt, model=model, **kwargs)
        text_response = result_dict["text"]
        
        # Cleanup and Parse
        clean_text = text_response.strip()
        import re
        json_match = re.search(r'(\{.*\}|\[.*\])', clean_text, re.DOTALL)
        if json_match:
            clean_text = json_match.group(1)
            
        if clean_text.startswith("```json"): clean_text = clean_text[7:]
        elif clean_text.startswith("```"): clean_text = clean_text[3:]
        if clean_text.endswith("```"): clean_text = clean_text[:-3]
        
        try:
            return json.loads(clean_text.strip())
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON: {clean_text}")
            raise

    # Sync compatibility wrappers if needed for legacy code not yet refactored
    def generate_text(self, prompt: str, model_type: str = "reasoning", temperature: float = 0.7) -> str:
        """DEPRECATED: Sync wrapper for backward compatibility."""
        model = "gemini-2.5-pro" if model_type == "reasoning" else "gemini-2.5-flash"
        # Run async loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
             # We can't block here if loop is running, this legacy method is dangerous in async ctx
             # But for legacy scripts it might be fine.
             # Best effort: use run_coroutine_threadsafe if we are in another thread, 
             # but here we assume simple usage.
             raise RuntimeError("Cannot call sync generate_text from within running loop. Use 'generate' instead.")
             
        return loop.run_until_complete(
            self.generate(prompt, model=model, temperature=temperature)
        )["text"]
