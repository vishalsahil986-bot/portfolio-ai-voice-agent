import numpy as np
from faster_whisper import WhisperModel
 
from config.settings import settings
from utils.logger import get_logger
 
logger = get_logger(__name__)