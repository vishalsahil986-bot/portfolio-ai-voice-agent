from enum import Enum

from utils.logger import get_logger

logger = get_logger(__name__)

class CallState(str, Enum):
    LISTENING = "LISTENING"   # waiting for / receiving user audio
    THINKING = "THINKING"     # STT done, waiting on LLM (+ RAG/memory) response
    SPEAKING = "SPEAKING"     # streaming TTS audio back to the user

# States the machine is allowed to move to, from each current state.
_ALLOWED_TRANSITIONS = {
    CallState.LISTENING: {CallState.THINKING},
    CallState.THINKING: {CallState.SPEAKING, CallState.LISTENING},  # LISTENING = e.g. LLM error, retry
    CallState.SPEAKING: {CallState.LISTENING},  # includes barge-in interrupts
}