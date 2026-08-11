from datetime import datetime, timedelta, timezone
from typing import List, Optional
 
import motor.motor_asyncio
 
from config.settings import settings
from utils.logger import get_logger
 
logger = get_logger(__name__)

class MemoryManager:
    def __init__(self, uri: str = None, db_name: str = None):
        self.uri = uri or settings.MONGODB_URI
        self.db_name = db_name or settings.MONGODB_DB_NAME
        self.is_configured = bool(self.uri)
 
        if not self.is_configured:
            logger.warning(
                "No MONGODB_URI configured — memory will not be persisted. "
                "Set MONGODB_URI in .env to enable long-term memory."
            )
            self._client = None
            self._db = None
        else:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(self.uri)
            self._db = self._client[self.db_name]