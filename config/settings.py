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