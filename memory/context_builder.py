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
 