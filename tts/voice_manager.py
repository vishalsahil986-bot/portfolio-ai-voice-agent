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