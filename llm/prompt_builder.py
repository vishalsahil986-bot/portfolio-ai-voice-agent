from typing import List
 
from google.genai import types

SYSTEM_INSTRUCTION = (
    "You are a helpful, friendly voice assistant on a live phone/voice call. "
    "Keep replies short and conversational — 1 to 3 sentences, like natural "
    "spoken conversation, not a written essay. Never use markdown, bullet "
    "points, numbered lists, or any text formatting — everything you say "
    "gets read aloud by a text-to-speech engine, so it must sound natural "
    "when spoken, not read off a page."
)


def build_contents_with_context(
    conversation_history: List[dict],
    new_user_text: str,
    retrieved_context: str = "",
) -> List[types.Content]:
    """Same as build_contents but injects RAG context into the user turn."""
    context_prefix = (
        f"[Relevant context from knowledge base:\n{retrieved_context}\n]\n\n"
        if retrieved_context else ""
    )
    contents = [
        types.Content(role=turn["role"], parts=[types.Part(text=turn["text"])])
        for turn in conversation_history
    ]
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part(text=f"{context_prefix}{new_user_text}")]
        )
    )
    return contents