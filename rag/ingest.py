import glob
import hashlib
import os
from typing import List
 
from rag.embeddings import embedding_service
from rag.vector_store import vector_store
from utils.logger import get_logger
 
logger = get_logger(__name__)

KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base")
CHUNK_SIZE = 800     
CHUNK_OVERLAP = 100   

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []
 
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start = end - overlap 
    return [c for c in chunks if c]
 
 
 