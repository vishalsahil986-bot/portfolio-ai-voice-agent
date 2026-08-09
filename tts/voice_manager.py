from typing import List
 
from elevenlabs import ElevenLabs
from elevenlabs.core.api_error import ApiError
 
from config.settings import settings
from utils.logger import get_logger
 
logger = get_logger(__name__)

class AllElevenLabsKeysExhausted(Exception):
    """Raised when every key in the rotation pool has failed with a quota/auth error."""
    pass

class ElevenLabsVoiceManager:
    def __init__(self, api_keys: List[str] = None, voice_id: str = None, model_id: str = None):
        self.api_keys = api_keys if api_keys is not None else settings.ELEVENLABS_API_KEYS
        self.voice_id = voice_id or settings.ELEVENLABS_VOICE_ID
        self.model_id = model_id or settings.ELEVENLABS_MODEL_ID
 
        if not self.api_keys:
            logger.warning("No ElevenLabs API keys configured — TTS will fail until .env is filled in")
 
        self._current_index = 0
        self._client = self._build_client() if self.api_keys else None

    def _build_client(self) -> ElevenLabs:
        return ElevenLabs(api_key=self.api_keys[self._current_index])
 
    def _rotate_to_next_key(self) -> bool:
        """Move to the next key in the pool. Returns False if we've already tried them all."""
        if self._current_index + 1 >= len(self.api_keys):
            return False
        self._current_index += 1
        logger.warning(
            f"ElevenLabs account {self._current_index} exhausted/unauthorized — "
            f"rotating to account {self._current_index + 1} of {len(self.api_keys)}"
        )
        self._client = self._build_client()
        return True

    @staticmethod
    def _is_quota_or_auth_error(exc: Exception) -> bool:
        status = getattr(exc, "status_code", None)
        return status in (401, 403, 429)
 
    def synthesize(self, text: str) -> bytes:
        """
        Convert text to speech, returns raw audio bytes (mp3 by default
        from the ElevenLabs API). Rotates through the key pool on
        quota/auth failures, raises AllElevenLabsKeysExhausted if every
        account is out.
        """
        if not self._client:
            raise RuntimeError("ElevenLabsVoiceManager has no API keys configured")
 
        keys_tried = 0
        while keys_tried < len(self.api_keys):
            try:
                audio_stream = self._client.text_to_speech.convert(
                    voice_id=self.voice_id,
                    model_id=self.model_id,
                    text=text,
                )
                return b"".join(audio_stream)
 
            except ApiError as e:
                keys_tried += 1
                if self._is_quota_or_auth_error(e) and self._rotate_to_next_key():
                    continue  # retry with the new key
                if keys_tried >= len(self.api_keys):
                    break
                raise  
 
        raise AllElevenLabsKeysExhausted(
            f"All {len(self.api_keys)} ElevenLabs accounts failed with quota/auth errors"
        )
 
voice_manager = ElevenLabsVoiceManager()