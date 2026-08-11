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

    #  Session CRUD                                                        
 
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Load the session document. Returns None if not found or expired."""
        if not self.is_configured:
            return None
        try:
            doc = await self._db.sessions.find_one({"session_id": session_id})
            if not doc:
                return None
 
            # Check expiry
            last_active = doc.get("last_active")
            if last_active:
                expiry = last_active + timedelta(hours=settings.SESSION_EXPIRY_HOURS)
                if datetime.now(timezone.utc) > expiry:
                    logger.info(f"[{session_id}] Session expired — clearing summaries")
                    await self._expire_session(session_id)
                    return None
 
            return doc
        except Exception as e:
            logger.error(f"[{session_id}] Failed to get session: {e}")
            return None

    async def _expire_session(self, session_id: str) -> None:
        """Wipe summaries and reset count — keeps the document for customer data."""
        try:
            await self._db.sessions.update_one(
                {"session_id": session_id},
                {"$set": {
                    "summaries": [],
                    "message_count": 0,
                    "last_active": datetime.now(timezone.utc),
                }},
            )
        except Exception as e:
            logger.error(f"[{session_id}] Failed to expire session: {e}")
 
    async def _touch_session(self, session_id: str) -> None:
        """Update last_active timestamp — called on every turn."""
        try:
            await self._db.sessions.update_one(
                {"session_id": session_id},
                {
                    "$set": {"last_active": datetime.now(timezone.utc)},
                    "$setOnInsert": {
                        "session_id": session_id,
                        "summaries": [],
                        "message_count": 0,
                    },
                },
                upsert=True,
            )
        except Exception as e:
            logger.error(f"[{session_id}] Failed to touch session: {e}")
