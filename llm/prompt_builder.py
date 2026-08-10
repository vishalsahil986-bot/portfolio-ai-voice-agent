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

def build_contents(conversation_history: List[dict], new_user_text: str) -> List[types.Content]:

    contents = [
        types.Content(role=turn["role"], parts=[types.Part(text=turn["text"])])
        for turn in conversation_history
    ]
    contents.append(types.Content(role="user", parts=[types.Part(text=new_user_text)]))
    return contents