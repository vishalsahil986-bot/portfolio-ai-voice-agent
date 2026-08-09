from typing import List

from elevenlabs import ElevenLabs
from elevenlabs.core.api_error import ApiError

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class AllElevenLabsKeysExhausted(Exception):
    """Raised when every account in the rotation pool has failed with a quota/auth error."""
    pass


class ElevenLabsVoiceManager:
    def __init__(self, account_pool: List[dict] = None, model_id: str = None):
        self.account_pool = account_pool if account_pool is not None else settings.ELEVENLABS_ACCOUNT_POOL
        self.model_id = model_id or settings.ELEVENLABS_MODEL_ID

        if not self.account_pool:
            logger.warning(
                "No complete ElevenLabs account (key + voice ID) configured — "
                "TTS will fail until .env is filled in"
            )

        self._current_index = 0
        self._client = self._build_client() if self.account_pool else None

    def _current_account(self) -> dict:
        return self.account_pool[self._current_index]

    def _build_client(self) -> ElevenLabs:
        return ElevenLabs(api_key=self._current_account()["api_key"])

    def _rotate_to_next_account(self) -> bool:
        """Move to the next {key, voice_id} pair. Returns False if we've already tried them all."""
        if self._current_index + 1 >= len(self.account_pool):
            return False
        self._current_index += 1
        logger.warning(
            f"ElevenLabs account {self._current_index} exhausted/unauthorized — "
            f"rotating to account {self._current_index + 1} of {len(self.account_pool)}"
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
        from the ElevenLabs API). Rotates through the account pool on
        quota/auth failures, raises AllElevenLabsKeysExhausted if every
        account is out.
        """
        if not self._client:
            raise RuntimeError("ElevenLabsVoiceManager has no accounts configured")

        accounts_tried = 0
        while accounts_tried < len(self.account_pool):
            try:
                audio_stream = self._client.text_to_speech.convert(
                    voice_id=self._current_account()["voice_id"],
                    model_id=self.model_id,
                    text=text,
                )
                return b"".join(audio_stream)

            except ApiError as e:
                accounts_tried += 1
                if self._is_quota_or_auth_error(e) and self._rotate_to_next_account():
                    continue  
                if accounts_tried >= len(self.account_pool):
                    break
                raise  

        raise AllElevenLabsKeysExhausted(
            f"All {len(self.account_pool)} ElevenLabs accounts failed with quota/auth errors"
        )


voice_manager = ElevenLabsVoiceManager()