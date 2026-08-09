import numpy as np
from faster_whisper import WhisperModel
 
from config.settings import settings
from utils.logger import get_logger
 
logger = get_logger(__name__)

class WhisperSTT:
    def __init__(self, model_size: str = None, device: str = None):
        self.model_size = model_size or settings.WHISPER_MODEL_SIZE
        self.device = device or settings.WHISPER_DEVICE
        self._model = None  