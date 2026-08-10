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

 