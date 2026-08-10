from typing import List
 
import numpy as np
from sentence_transformers import SentenceTransformer
 
from config.settings import settings
from utils.logger import get_logger
 
logger = get_logger(__name__)

class EmbeddingService:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._model = None  
 
    def _ensure_loaded(self) -> None:
        if self._model is None:
            logger.info(f"Loading embedding model '{self.model_name}' (first call only)...")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded")