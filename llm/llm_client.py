import os
from typing import Any, Dict, Optional, List, Union
import json
import logging
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content, SafetySetting, HarmCategory, HarmBlockThreshold, GenerationConfig
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class LLMClient:
    """Wrapper for Vertex AI Gemini models."""

    def __init__(self, project_id: Optional[str] = None, location: Optional[str] = None):
        """Initialize Vertex AI client.
        
        Args:
            project_id: GCP Project ID. Defaults to GOOGLE_CLOUD_PROJECT env var.
            location: Vertex AI location. Defaults to VERTEX_AI_LOCATION env var.
        """
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.environ.get("VERTEX_AI_LOCATION")
        
        # Check for legacy/alternative auth variable
        api_key = os.environ.get("GOOGLE_API_KEY")
        
        if not self.project_id:
            logger = logging.getLogger("llm_client")
            logger.warning("GOOGLE_CLOUD_PROJECT not set.")
            if api_key:
                logger.warning("Found GOOGLE_API_KEY. Note that Vertex AI SDK normally uses ADC (GOOGLE_APPLICATION_CREDENTIALS).")
        
        if not self.project_id or not self.location:
             # Try to be helpful if they provided API Key but not Project
             if api_key and not self.project_id:
                 raise ValueError("GOOGLE_CLOUD_PROJECT env var is missing. Even with an API Key, Vertex AI requires a valid Project ID.")
             raise ValueError("GOOGLE_CLOUD_PROJECT and VERTEX_AI_LOCATION must be set.")
            
        try:
            vertexai.init(project=self.project_id, location=self.location)
        except Exception as e:
            print(f"Failed to initialize Vertex AI: {e}")
            if api_key:
                print("Tip: If you are trying to use an API Key, ensure you have set up ADC locally or use the 'google-generativeai' library instead of Vertex AI if permissible.")
            raise

        self.reasoning_model_name = "gemini-2.5-pro"  # Use Pro for planning/reasoning
        self.fast_model_name = "gemini-2.5-flash"     # Use Flash for tasks/specialists

    def get_reasoning_model(self) -> GenerativeModel:
        """Returns the configured Gemini 2.5 Pro model."""
        return GenerativeModel(self.reasoning_model_name)

    def get_fast_model(self) -> GenerativeModel:
        """Returns the configured Gemini 2.5 Flash model."""
        return GenerativeModel(self.fast_model_name)

    def generate_text(self, 
                     prompt: str, 
                     model_type: str = "reasoning", 
                     temperature: float = 0.7) -> str:
        """Generates text response from the specified model.
        
        Args:
            prompt: The input prompt.
            model_type: 'reasoning' (Pro) or 'fast' (Flash).
            temperature: Generation temperature.
            
        Returns:
            The generated text content.
        """
        model = self.get_reasoning_model() if model_type == "reasoning" else self.get_fast_model()
        
        config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=8192,
        )
        # Remove the hacky fallback check since we imported it correctly now

        
        # Default safety settings - block only high probability of harm to allow simulation contexts
        # Note: In a real simulation, we might need adjustments, but sticking to safe defaults is good.
        safety_settings = [
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH
            ),
             SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH
            )
        ]

        try:
            response = model.generate_content(
                prompt,
                generation_config=config,
                safety_settings=safety_settings
            )
            if response.text:
                return response.text
            else:
                return "" # or raise specific error about blocked content
        except Exception as e:
            # In a real app, integrate retry logic here (e.g., using tenancy/backoff)
            print(f"Error calling Vertex AI: {e}")
            raise e

    def generate_structured_output(self, 
                                 prompt: str, 
                                 response_schema: Dict[str, Any],
                                 model_type: str = "fast") -> Dict[str, Any]:
        """Generates JSON output matching a schema.
        
        Args:
            prompt: The input prompt.
            response_schema: Pydantic model dict, or raw JSON schema dict.
            model_type: 'reasoning' (Pro) or 'fast' (Flash).
            
        Returns:
            Parsed JSON dictionary.
        """
        # Append schema instruction to prompt for better adherence (even with native JSON mode)
        full_prompt = f"{prompt}\n\nRespond with valid JSON matching this schema:\n{json.dumps(response_schema, indent=2)}"
        
        text_response = self.generate_text(full_prompt, model_type=model_type, temperature=0.2)
        
        # Clean up Markdown code blocks if present
        clean_text = text_response.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            print(f"Failed to parse JSON: {text_response}")
            raise
