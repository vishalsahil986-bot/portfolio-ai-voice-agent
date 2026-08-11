from typing import List
 
from google.genai import types
 
from memory.memory_manager import memory_manager
from utils.logger import get_logger
 
logger = get_logger(__name__)

_MEMORY_BLOCK_TEMPLATE = """[Conversation history summary:
{summaries}]"""
 
_RAG_BLOCK_TEMPLATE = """[Relevant context from knowledge base:
{context}]"""
 
_SUMMARY_ITEM_TEMPLATE = (
    "- User wanted: {user_intent} | "
    "Bot replied: {bot_response} | "
    "Context: {context}"
)

def _format_summaries(summaries: List[dict]) -> str:
    """Format structured summary dicts into a compact readable block."""
    lines = []
    for i, s in enumerate(summaries, 1):
        lines.append(
            f"Exchange {i}: " +
            _SUMMARY_ITEM_TEMPLATE.format(
                user_intent=s.get("user_intent", ""),
                bot_response=s.get("bot_response", ""),
                context=s.get("context", ""),
            )
        )
    return "\n".join(lines)

async def build_gemini_context(
    session_id: str,
    conversation_history: List[dict],
    new_user_text: str,
    retrieved_context: str = "",
    message_count: int = 0,
) -> List[types.Content]:
    """
    Assemble the full contents list for a Gemini call.
 
    session_id: used to load summaries from MongoDB
    conversation_history: in-RAM recent turns from Session
    new_user_text: what the user just said (transcribed by Whisper)
    retrieved_context: RAG chunks from retriever.retrieve() — "" if none
    message_count: current message count — drives which context mode to use
 
    Returns List[types.Content] ready to pass as `contents` to Gemini.
    """
    contents: List[types.Content] = []

    #  Message 1: no history yet
    if message_count <= 1:
        logger.info(f"[{session_id}] Message 1 — sending direct, no history")
        contents.append(_make_user_turn(new_user_text, retrieved_context))
        return contents

    # ── Message 2: include raw first exchange ────────────────────────
    if message_count == 2:
        logger.info(f"[{session_id}] Message 2 — including raw first exchange")
        for turn in conversation_history:
            contents.append(
                types.Content(
                    role=turn["role"],
                    parts=[types.Part(text=turn["text"])],
                )
            )
        contents.append(_make_user_turn(new_user_text, retrieved_context))
        return contents
 