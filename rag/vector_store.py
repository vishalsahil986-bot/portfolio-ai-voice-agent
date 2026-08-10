from typing import List, Optional
from pinecone import Pinecone, ServerlessSpec
 
from config.settings import settings 
from utils.logger import get_logger
 
logger = get_logger(__name__)