from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    #Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    #LLM (Gemini)
    GEMINI_API_KEY1: str = ""
    GEMINI_API_KEY2: str = ""
    GEMINI_API_KEY3: str = ""
    GEMINI_API_KEY4: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash"

    @property
    def GEMINI_API_KEYS(self) -> list[str]:
        """Ordered rotation pool — empty/unset slots are dropped automatically."""
        keys = [self.GEMINI_API_KEY1, self.GEMINI_API_KEY2, self.GEMINI_API_KEY3, self.GEMINI_API_KEY4]
        return [k for k in keys if k.strip()]

    #STT (Whisper, local/open-source)
    WHISPER_MODEL_SIZE: str = "base" # tiny | base | small | medium | large
    WHISPER_DEVICE: str = "cpu" # cpu | cuda

    #TTS (ElevenLabs) 
    ELEVENLABS_API_KEYS1: str = ""
    ELEVENLABS_API_KEYS2: str = ""
    ELEVENLABS_API_KEYS3: str = ""
    ELEVENLABS_VOICE_ID: str = ""

    @property
    def ELEVENLABS_API_KEYS(self) -> List[str]:
        keys = [self.ELEVENLABS_API_KEYS1, self.ELEVENLABS_API_KEYS2, self.ELEVENLABS_API_KEYS3]
        return [k for k in keys if k.strip()]

    #Audio
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHUNK_MS: int = 30  # size of each audio chunk processed by VAD
    SILENCE_THRESHOLD_MS: int = 700  # how long silence must last before we treat speech as finished