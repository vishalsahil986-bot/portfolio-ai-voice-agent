import collections
from typing import Optional
 
import webrtcvad
 
from config.settings import settings
from utils.logger import get_logger
 
logger = get_logger(__name__)

class VoiceActivityDetector:
    def __init__(
        self,
        aggressiveness: int = 2,
        sample_rate: int = None,
        frame_ms: int = None,
        speech_confirm_frames: int = 3,
        silence_confirm_ms: int = None,
    ):