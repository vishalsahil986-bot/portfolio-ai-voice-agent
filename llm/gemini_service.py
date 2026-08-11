from typing import List
 
from google import genai
from google.genai import types
from google.genai.errors import APIError
 
from config.settings import settings
from llm.prompt_builder import SYSTEM_INSTRUCTION
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

    def _build_client(self) -> genai.Client:
        return genai.Client(api_key=self.api_keys[self._current_index])
 
    def _rotate_to_next_key(self) -> bool:
        """Move to the next key in the pool. Returns False if we've already tried them all."""
        if self._current_index + 1 >= len(self.api_keys):
            return False
        self._current_index += 1
        logger.warning(
            f"Gemini key {self._current_index} exhausted/unauthorized — "
            f"rotating to key {self._current_index + 1} of {len(self.api_keys)}"
        )
        self._client = self._build_client()
        return True

    @staticmethod
    def _is_quota_or_auth_error(exc: Exception) -> bool:
        code = getattr(exc, "code", None)
        return code in (401, 403, 429)
 
    def generate_reply(self, conversation_history: List[dict], user_text: str) -> str:
        """
        conversation_history: [{"role": "user"|"model", "text": str}, ...]
        for this call so far (Phase 3: full history, no trimming —
        Phase 5 replaces this with summarized context).
        user_text: what the user just said (already transcribed by Whisper).
 
        Returns the agent's reply text. Rotates through the key pool
        on quota/auth failures, raises AllGeminiKeysExhausted if every
        key is out.
        """
        if not self._client:
            raise RuntimeError("GeminiService has no API keys configured")
 
        contents = build_contents(conversation_history, user_text)
 
        keys_tried = 0
        while keys_tried < len(self.api_keys):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
                )
                text = (response.text or "").strip()
                logger.info(f"Gemini replied: '{text}'")
                return text
 
            except APIError as e:
                keys_tried += 1
                if self._is_quota_or_auth_error(e) and self._rotate_to_next_key():
                    continue  
                if keys_tried >= len(self.api_keys):
                    break
                raise  
 
        raise AllGeminiKeysExhausted(
            f"All {len(self.api_keys)} Gemini keys failed with quota/auth errors"
        )

    def generate_reply_from_contents(self, contents: list) -> str:
        """
        Same as generate_reply() but accepts pre-built contents list
        from memory/context_builder.py — used by Phase 5 websocket_routes.py.
        """
        if not self._client:
            raise RuntimeError("GeminiService has no API keys configured")

        keys_tried = 0
        while keys_tried < len(self.api_keys):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION
                    ),
                )
                text = (response.text or "").strip()
                logger.info(f"Gemini replied: '{text}'")
                return text

            except APIError as e:
                keys_tried += 1
                if self._is_quota_or_auth_error(e) and self._rotate_to_next_key():
                    continue
                if keys_tried >= len(self.api_keys):
                    break
                raise

        raise AllGeminiKeysExhausted(
            f"All {len(self.api_keys)} Gemini keys failed with quota/auth errors"
        )
    

gemini_service = GeminiService()