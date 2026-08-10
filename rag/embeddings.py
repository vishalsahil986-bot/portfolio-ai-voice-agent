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

    def embed_text(self, text: str) -> List[float]:
        """Embed a single string (a query or a chunk). Returns a plain list of floats — what Pinecone expects."""
        self._ensure_loaded()
        vector: np.ndarray = self._model.encode(text, normalize_embeddings=True)
        return vector.tolist()