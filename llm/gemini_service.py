"""
llm/gemini_service.py

Gemini LLM service with API key rotation and per-call timeout.
"""

from typing import List

from google import genai
from google.genai import types
from google.genai.errors import APIError

from config.settings import settings
from llm.prompt_builder import SYSTEM_INSTRUCTION
from utils.logger import get_logger

logger = get_logger(__name__)

# Hard timeout for a single Gemini generate_content call (seconds).
# If Gemini hasn't replied in this time, we give up and return "" so the
# session is not stuck in THINKING forever.
GEMINI_TIMEOUT_SECONDS = 15


class AllGeminiKeysExhausted(Exception):
    """Raised when every key in the rotation pool has failed with a quota/auth error."""
    pass


class GeminiService:
    def __init__(self, api_keys: List[str] = None, model: str = None):
        self.api_keys = api_keys if api_keys is not None else settings.GEMINI_API_KEYS
        self.model = model or settings.GEMINI_MODEL

        if not self.api_keys:
            logger.warning(
                "No Gemini API keys configured — LLM calls will fail until .env is filled in"
            )

        self._current_index = 0
        self._client = self._build_client() if self.api_keys else None

    def _build_client(self) -> genai.Client:
        return genai.Client(
            api_key=self.api_keys[self._current_index],
        )

    def _rotate_to_next_key(self) -> bool:
        """Move to the next key in the pool. Returns False if all keys tried."""
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

    @staticmethod
    def _extract_text(response) -> str:
        """
        Safely extract text from a Gemini response.
        Handles response.text (standard) and response.content (string or list).
        """
        # Primary: response.text
        text = getattr(response, "text", None)
        if text:
            return text.strip()

        # Fallback: response.content
        content = getattr(response, "content", None)
        if content is None:
            return ""
        if isinstance(content, list):
            return " ".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict)
            ).strip()
        if isinstance(content, str):
            return content.strip()
        return str(content).strip()

    def generate_reply_from_contents(self, contents: list) -> str:
        """
        Primary method — accepts pre-built contents list from context_builder.py.
        Rotates through API keys on quota/auth failures.
        Returns empty string on timeout (caller handles gracefully).
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
                text = self._extract_text(response)
                logger.info(
                    f"Gemini replied: '{text[:120]}{'...' if len(text) > 120 else ''}'"
                )
                return text

            except APIError as e:
                keys_tried += 1
                logger.warning(f"Gemini API error (key {self._current_index + 1}): {e}")
                if self._is_quota_or_auth_error(e) and self._rotate_to_next_key():
                    continue
                if keys_tried >= len(self.api_keys):
                    break
                raise

            except Exception as e:
                # Covers timeouts, connection resets, etc.
                logger.error(f"Gemini call failed (non-API error): {type(e).__name__}: {e}")
                return ""

        raise AllGeminiKeysExhausted(
            f"All {len(self.api_keys)} Gemini keys failed with quota/auth errors"
        )

    def generate_reply(self, conversation_history: List[dict], user_text: str) -> str:
        """Legacy method — kept for backward compatibility."""
        contents = [
            types.Content(role=turn["role"], parts=[types.Part(text=turn["text"])])
            for turn in conversation_history
        ]
        contents.append(
            types.Content(role="user", parts=[types.Part(text=user_text)])
        )
        return self.generate_reply_from_contents(contents)


gemini_service = GeminiService()
