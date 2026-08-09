from typing import List
 
from elevenlabs import ElevenLabs
from elevenlabs.core.api_error import ApiError
 
from config.settings import settings
from utils.logger import get_logger
 
logger = get_logger(__name__)