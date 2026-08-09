from enum import Enum

from utils.logger import get_logger

logger = get_logger(__name__)

class CallState(str, Enum):
    LISTENING = "LISTENING"   # waiting for / receiving user audio
    THINKING = "THINKING"     # STT done, waiting on LLM (+ RAG/memory) response
    SPEAKING = "SPEAKING"     # streaming TTS audio back to the user