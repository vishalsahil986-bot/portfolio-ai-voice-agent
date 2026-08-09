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

    def _ensure_loaded(self) -> None:
        if self._model is None:
            logger.info(f"Loading faster-whisper model '{self.model_size}' on {self.device} (first call only)...")
            compute_type = "float16" if self.device == "cuda" else "int8"
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=compute_type)
            logger.info("faster-whisper model loaded")

    @staticmethod
    def pcm_bytes_to_float32(pcm_bytes: bytes) -> np.ndarray:
        """faster-whisper wants float32 samples in [-1, 1]; our pipeline carries 16-bit PCM."""
        int16_samples = np.frombuffer(pcm_bytes, dtype=np.int16)
        return int16_samples.astype(np.float32) / 32768.0