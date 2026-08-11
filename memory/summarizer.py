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

def _parse_summary(raw: str) -> Optional[dict]:
    """
    Safely parse Gemini's JSON response.
    Strips markdown fences if Gemini adds them despite the prompt.
    Returns None if parsing fails — caller handles the fallback.
    """
    try:
        clean = raw.strip()
        if clean.startswith("```"):

            lines = clean.split("\n")
            clean = "\n".join(lines[1:-1])
        parsed = json.loads(clean)

        if all(k in parsed for k in ("user_intent", "bot_response", "context")):
            return parsed
        logger.warning("Summary JSON missing required fields")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse summary JSON: {e} — raw: {raw[:200]}")
        return None