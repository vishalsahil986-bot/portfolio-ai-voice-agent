import asyncio
import json
from typing import Optional
 
from memory.memory_manager import memory_manager
from config.settings import settings
from utils.logger import get_logger
 
logger = get_logger(__name__)

_SUMMARIZE_PROMPT = """Summarize this conversation exchange in JSON format.
Return ONLY valid JSON, no markdown, no explanation, no preamble.
 
Exchange:
User: {user_text}
Assistant: {bot_text}
 
Return exactly this structure:
{{
  "user_intent": "what the user was asking or trying to do (one sentence)",
  "bot_response": "what the assistant replied or did (one sentence)",
  "context": "key facts to remember for the rest of the call (one sentence)"
}}"""