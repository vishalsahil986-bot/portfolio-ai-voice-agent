import asyncio
import json
from typing import Optional
 
from memory.memory_manager import memory_manager
from config.settings import settings
from utils.logger import get_logger
 
logger = get_logger(__name__)