import asyncio
import json
from typing import Optional

from google.genai import types
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


async def summarize_exchange_in_background(
    session_id: str,
    user_text: str,
    bot_text: str,
    message_count: int,
) -> None:
    """
    Decide whether to summarize and fire as background task.

    message_count: the CURRENT count after this turn.
    Summarization starts from message 3 onwards — first two messages
    are kept raw (first exchange stays in conversation_history).

    Called from websocket_routes.py after every completed turn.
    """
    if not memory_manager.is_configured:
        return

    if message_count < 3:
        logger.info(f"[{session_id}] Message {message_count} — no summarization yet")
        return

    logger.info(
        f"[{session_id}] Message {message_count} — "
        f"firing background summarization of previous exchange"
    )
    asyncio.create_task(
        _run_summarization(session_id, user_text, bot_text)
    )


async def _run_summarization(
    session_id: str,
    user_text: str,
    bot_text: str,
) -> None:
    """
    The actual summarization — runs in background, errors never surface to user.
    Uses gemini_service with temperature 0.1 for consistent structured output.
    """
    try:
        from llm.gemini_service import gemini_service

        prompt = _SUMMARIZE_PROMPT.format(
            user_text=user_text,
            bot_text=bot_text,
        )

        logger.info(f"[{session_id}] Summarizing exchange with Gemini (low temp)...")

        contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
        raw_summary = await asyncio.to_thread(
            gemini_service.generate_reply_from_contents,
            contents,
        )

        if not raw_summary:
            logger.warning(f"[{session_id}] Gemini returned empty summary — skipping")
            return

        summary = _parse_summary(raw_summary)
        if not summary:
            summary = {
                "user_intent": user_text[:200],
                "bot_response": bot_text[:200],
                "context": "Exchange summarization failed — raw text stored",
            }
            logger.warning(f"[{session_id}] Using fallback plain-text summary")

        await memory_manager.append_summary(session_id, summary)
        logger.info(f"[{session_id}] Exchange summarized and saved ✅")

    except Exception as e:
        logger.error(f"[{session_id}] Summarization task failed: {e}")