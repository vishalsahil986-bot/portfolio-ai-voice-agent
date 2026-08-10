from typing import List
 
from google import genai
from google.genai import types
from google.genai.errors import APIError
 
from config.settings import settings
from llm.prompt_builder import SYSTEM_INSTRUCTION, build_contents
from utils.logger import get_logger
 
logger = get_logger(__name__)

class AllGeminiKeysExhausted(Exception):
    """Raised when every key in the rotation pool has failed with a quota/auth error."""
    pass

class GeminiService:
    def __init__(self, api_keys: List[str] = None, model: str = None):
        self.api_keys = api_keys if api_keys is not None else settings.GEMINI_API_KEYS
        self.model = model or settings.GEMINI_MODEL
 
        if not self.api_keys:
            logger.warning("No Gemini API keys configured — LLM calls will fail until .env is filled in")
 
        self._current_index = 0
        self._client = self._build_client() if self.api_keys else None