from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    #  Server 
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    #  LLM (Gemini) 
    GEMINI_API_KEY1: str = ""
    GEMINI_API_KEY2: str = ""
    GEMINI_API_KEY3: str = ""
    GEMINI_API_KEY4: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    @property
    def GEMINI_API_KEYS(self) -> List[str]:
        """Ordered rotation pool — empty/unset slots are dropped automatically."""
        keys = [self.GEMINI_API_KEY1, self.GEMINI_API_KEY2, self.GEMINI_API_KEY3, self.GEMINI_API_KEY4]
        return [k for k in keys if k.strip()]

    #  STT (Whisper, local/open-source) 
    WHISPER_MODEL_SIZE: str = "base"  # tiny | base | small | medium | large
    WHISPER_DEVICE: str = "cpu"  # cpu | cuda

    #  TTS (ElevenLabs) 
    ELEVENLABS_API_KEYS1: str = ""
    ELEVENLABS_VOICE_ID1: str = ""
    ELEVENLABS_API_KEYS2: str = ""
    ELEVENLABS_VOICE_ID2: str = ""
    ELEVENLABS_API_KEYS3: str = ""
    ELEVENLABS_VOICE_ID3: str = ""
    ELEVENLABS_API_KEYS4: str = ""
    ELEVENLABS_VOICE_ID4: str = ""
    ELEVENLABS_API_KEYS5: str = ""
    ELEVENLABS_VOICE_ID5: str = ""
    ELEVENLABS_API_KEYS6: str = ""
    ELEVENLABS_VOICE_ID6: str = ""
    ELEVENLABS_API_KEYS7: str = ""
    ELEVENLABS_VOICE_ID7: str = ""
    ELEVENLABS_API_KEYS8: str = ""
    ELEVENLABS_VOICE_ID8: str = ""
    ELEVENLABS_MODEL_ID: str = "eleven_flash_v2_5"

    @property
    def ELEVENLABS_ACCOUNT_POOL(self) -> List[dict]:
        """
        Ordered list of {"api_key": ..., "voice_id": ...} pairs — a
        slot is only included if BOTH its key and voice ID are set.
        A key with no matching voice ID is useless (nothing to
        synthesize with), so it's silently dropped rather than
        included half-broken.
        """
        pairs = [
            (self.ELEVENLABS_API_KEYS1, self.ELEVENLABS_VOICE_ID1),
            (self.ELEVENLABS_API_KEYS2, self.ELEVENLABS_VOICE_ID2),
            (self.ELEVENLABS_API_KEYS3, self.ELEVENLABS_VOICE_ID3),
        ]
        return [
            {"api_key": key.strip(), "voice_id": voice.strip()}
            for key, voice in pairs
            if key.strip() and voice.strip()
        ]

    #  Audio 
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHUNK_MS: int = 30  
    SILENCE_THRESHOLD_MS: int = 700  


    #  RAG (Pinecone + HuggingFace)
    PINECONE_API_KEY: str = Field(default="")
    PINECONE_INDEX_NAME: str = "voice-agent"
    PINECONE_CLOUD: str = "aws"
    PINECONE_REGION: str = "us-east-1"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    RAG_TOP_K: int = 3


@lru_cache
def get_settings() -> Settings:
    """Settings are read from env once and cached — call get_settings() anywhere you need config."""
    return Settings()


settings = get_settings()