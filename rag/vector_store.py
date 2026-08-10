from typing import List, Optional
from pinecone import Pinecone, ServerlessSpec
 
from config.settings import settings 
from utils.logger import get_logger
 
logger = get_logger(__name__)

 
class PineconeVectorStore:
    def __init__(
        self,
        api_key: str = None,
        index_name: str = None,
        cloud: str = None,
        region: str = None,
        dimension: int = None,
    ):
        self.api_key = api_key or settings.PINECONE_API_KEY
        self.index_name = index_name or settings.PINECONE_INDEX_NAME
        self.cloud = cloud or settings.PINECONE_CLOUD
        self.region = region or settings.PINECONE_REGION
        self.dimension = dimension or settings.EMBEDDING_DIMENSION
 
        self.is_configured = bool(self.api_key)
        if not self.is_configured:
            logger.warning("No PINECONE_API_KEY configured — RAG retrieval will be skipped until .env is filled in")
 
        self._pc: Optional[Pinecone] = Pinecone(api_key=self.api_key) if self.is_configured else None
        self._index = None  # lazy — created/connected on first real use, not at import time
 