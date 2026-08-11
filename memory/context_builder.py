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
 