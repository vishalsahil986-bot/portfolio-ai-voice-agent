from typing import List
 
import numpy as np
from sentence_transformers import SentenceTransformer
 
from config.settings import settings
from utils.logger import get_logger
 
logger = get_logger(__name__)