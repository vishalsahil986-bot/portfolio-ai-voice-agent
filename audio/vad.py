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
        """
        aggressiveness: 0 (least aggressive, more false positives on
            speech) to 3 (most aggressive, filters more background
            noise but can clip soft speech). 2 is a reasonable default
            for a phone/mic call.
        speech_confirm_frames: how many consecutive speech frames are
            needed before we declare "user started talking" — avoids
            triggering on a single cough or click.
        silence_confirm_ms: how long silence must persist before we
            declare "user finished talking" — defaults to
            settings.SILENCE_THRESHOLD_MS.
        """
        if aggressiveness not in (0, 1, 2, 3):
            raise ValueError("aggressiveness must be 0-3")