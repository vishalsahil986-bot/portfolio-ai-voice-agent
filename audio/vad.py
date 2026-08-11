import collections
from typing import Optional
 
import webrtcvad
 
from config.settings import settings
from utils.logger import get_logger
 
logger = get_logger(__name__)

class VoiceActivityDetector:
    def __init__(
        self,
        aggressiveness: int = 3,
        sample_rate: int = None,
        frame_ms: int = None,
        speech_confirm_frames: int = 5,
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

        self.sample_rate = sample_rate or settings.AUDIO_SAMPLE_RATE
        self.frame_ms = frame_ms or settings.AUDIO_CHUNK_MS
        if self.frame_ms not in (10, 20, 30):
            raise ValueError("frame_ms must be 10, 20, or 30 (webrtcvad requirement)")
 
        self._vad = webrtcvad.Vad(aggressiveness)
        self._bytes_per_frame = int(self.sample_rate * (self.frame_ms / 1000.0) * 2)  # 16-bit = 2 bytes/sample
 
        self.speech_confirm_frames = speech_confirm_frames
        self.silence_confirm_frames = int(
            (silence_confirm_ms or settings.SILENCE_THRESHOLD_MS) / self.frame_ms
        )
 
        # Rolling state used by process_frame()
        self._recent_speech_flags = collections.deque(maxlen=speech_confirm_frames)
        self._consecutive_silence_frames = 0
        self.is_speaking = False

    def is_speech_frame(self, frame: bytes) -> bool:
        """Raw per-frame check, no state. frame must be exactly one frame's worth of PCM bytes."""
        if len(frame) != self._bytes_per_frame:
            raise ValueError(
                f"Expected {self._bytes_per_frame} bytes for a {self.frame_ms}ms frame "
                f"at {self.sample_rate}Hz, got {len(frame)}"
            )
        return self._vad.is_speech(frame, self.sample_rate)

    def process_frame(self, frame: bytes) -> Optional[str]:
        """
        Feed one frame at a time. Returns:
          "speech_started"  - user just started talking (state flips False -> True)
          "speech_ended"    - user just stopped talking, long enough to count as turn end
          None              - no state change yet, keep buffering
        """
        speech = self.is_speech_frame(frame)
        self._recent_speech_flags.append(speech)

        if not self.is_speaking:
            if len(self._recent_speech_flags) == self.speech_confirm_frames and all(self._recent_speech_flags):
                self.is_speaking = True
                self._consecutive_silence_frames = 0
                logger.info("VAD: speech_started")
                return "speech_started"
            return None

        if speech:
            self._consecutive_silence_frames = 0
        else:
            self._consecutive_silence_frames += 1
            if self._consecutive_silence_frames >= self.silence_confirm_frames:
                self.is_speaking = False
                self._recent_speech_flags.clear()
                logger.info("VAD: speech_ended")
                return "speech_ended"
 
        return None

    def reset(self) -> None:
        self._recent_speech_flags.clear()
        self._consecutive_silence_frames = 0
        self.is_speaking = False