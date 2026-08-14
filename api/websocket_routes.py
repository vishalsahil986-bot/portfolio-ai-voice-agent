"""
api/websocket_routes.py

WebSocket endpoint: full voice agent pipeline.

Pipeline order per turn:
  VAD speech_ended
    → Whisper STT
    → Load/create MongoDB session
    → Retrieve RAG chunks
    → build_gemini_context()   [3-phase memory]
    → Gemini LLM
    → bot_response
    → ElevenLabs TTS
    → Send audio + transcript via WebSocket
    → asyncio.create_task(summarize_exchange_in_background())
    → Update session state (last_messages, message_count)
"""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from audio.stt_whisper import whisper_stt
from call.call_state_machine import CallState
from call.session_manager import Session, session_manager
from elevenlabs.core.api_error import ApiError
from google.genai.errors import APIError as GeminiApiError
from llm.gemini_service import AllGeminiKeysExhausted, gemini_service
from memory.context_builder import build_gemini_context
from memory.memory_manager import memory_manager
from memory.summarizer import summarize_exchange_in_background
from rag.retriever import retriever
from tts.voice_manager import AllElevenLabsKeysExhausted, voice_manager
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

_MIN_TRANSCRIPT_LENGTH = 4
_JUNK_PHRASES = frozenset([". . .", "...", "you", "bye", "thanks", "thank you"])

# Minimum audio duration (seconds) to bother transcribing — prevents Whisper
# wasting time on sub-200ms noise bursts that passed VAD.
_MIN_AUDIO_DURATION_SECONDS = 0.4


async def _handle_speech_started(session: Session, websocket: WebSocket) -> None:
    if session.state_machine.state == CallState.SPEAKING:
        # Barge-in disabled — ignore speech while agent is talking
        return
    session.utterance_buffer.reset()


async def _handle_speech_ended(session: Session, websocket: WebSocket) -> None:
    """
    Full turn processing pipeline.
    Always returns the session to LISTENING state — even on errors —
    so the agent never gets permanently stuck in THINKING.
    """
    audio = session.utterance_buffer.get_audio()
    session.utterance_buffer.reset()

    if not audio:
        return

    # Reject very short audio bursts that slipped past VAD (< 400ms)
    duration = len(audio) / 2 / 16000  # 16-bit mono at 16kHz
    if duration < _MIN_AUDIO_DURATION_SECONDS:
        logger.info(f"[{session.session_id}] Audio too short ({duration:.2f}s) — skipping")
        return

    session.interrupted = False

    # Guard against concurrent processing
    if session.state_machine.state != CallState.LISTENING:
        logger.info(f"[{session.session_id}] Skipping — still processing previous turn")
        return

    session.state_machine.transition(CallState.THINKING)

    try:
        await _process_turn(session, websocket, audio)
    except Exception as e:
        logger.error(f"[{session.session_id}] Unhandled error in turn processing: {e}")
    finally:
        # ALWAYS return to LISTENING so the session is never stuck
        if session.state_machine.state != CallState.LISTENING:
            session.state_machine.interrupt()


async def _process_turn(session: Session, websocket: WebSocket, audio: bytes) -> None:
    """Inner pipeline — separated so _handle_speech_ended can always clean up."""

    # ── STT ───────────────────────────────────────────────────────────────────
    user_text = await asyncio.to_thread(whisper_stt.transcribe, audio, language="en")

    if not user_text or len(user_text.strip()) < _MIN_TRANSCRIPT_LENGTH:
        logger.info(f"[{session.session_id}] Transcript too short or empty — skipping")
        return

    if user_text.strip().lower() in _JUNK_PHRASES:
        logger.info(f"[{session.session_id}] Filtered junk: '{user_text}'")
        return

    await websocket.send_json({"type": "transcript", "text": user_text})

    # ── Session: get pre-increment message count ───────────────────────────────
    # Returns count BEFORE incrementing: 0=Phase1, 1=Phase2, 2+=Phase3
    message_count = await memory_manager.increment_message_count(session.session_id)

    # ── RAG retrieval ─────────────────────────────────────────────────────────
    retrieved_context = await asyncio.to_thread(retriever.retrieve, user_text)

    # ── Build memory context (3-phase algorithm) ──────────────────────────────
    contents = await build_gemini_context(
        session_id=session.session_id,
        new_user_text=user_text,
        retrieved_context=retrieved_context,
        message_count=message_count,
    )

    # ── Gemini LLM ────────────────────────────────────────────────────────────
    try:
        bot_text = await asyncio.to_thread(
            gemini_service.generate_reply_from_contents, contents
        )
    except AllGeminiKeysExhausted:
        logger.error(f"[{session.session_id}] All Gemini keys exhausted")
        return
    except GeminiApiError as e:
        logger.error(f"[{session.session_id}] Gemini API error: {e}")
        return

    if not bot_text:
        logger.warning(f"[{session.session_id}] Gemini returned empty reply — skipping TTS")
        return

    # ── ElevenLabs TTS ────────────────────────────────────────────────────────
    session.state_machine.transition(CallState.SPEAKING)

    try:
        reply_audio = await asyncio.to_thread(voice_manager.synthesize, bot_text)
    except AllElevenLabsKeysExhausted:
        logger.error(f"[{session.session_id}] All ElevenLabs accounts exhausted")
        session.state_machine.interrupt()
        return
    except ApiError as e:
        logger.error(f"[{session.session_id}] ElevenLabs TTS error: {e}")
        session.state_machine.interrupt()
        return

    # ── Send response ─────────────────────────────────────────────────────────
    if session.interrupted:
        logger.info(f"[{session.session_id}] Reply discarded — barge-in during synthesis")
    else:
        await websocket.send_json({"type": "reply_text", "text": bot_text})
        await websocket.send_bytes(reply_audio)

    if session.state_machine.state == CallState.SPEAKING:
        session.state_machine.transition(CallState.LISTENING)

    # ── Non-blocking background summarization ─────────────────────────────────
    await summarize_exchange_in_background(
        session_id=session.session_id,
        user_text=user_text,
        bot_text=bot_text,
        message_count=message_count,
    )

    # ── Update last_messages in MongoDB (used for Phase 2 context) ───────────
    asyncio.create_task(
        memory_manager.update_last_messages(
            session_id=session.session_id,
            user_message=user_text,
            assistant_message=bot_text,
        )
    )

    # Mirror to in-RAM session
    session.conversation_history.append({"role": "user", "text": user_text})
    session.conversation_history.append({"role": "model", "text": bot_text})
    session.message_count = message_count + 1
    session.last_messages = {"user": user_text, "assistant": bot_text}


@router.websocket("/ws/call")
async def call_websocket(websocket: WebSocket):
    await websocket.accept()

    session = session_manager.create_session()
    await memory_manager.create_session(session.session_id)

    await websocket.send_json({
        "type": "session_started",
        "session_id": session.session_id,
    })
    await websocket.send_json({"type": "play_greeting"})

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(code=message.get("code", 1000))

            if "bytes" in message and message["bytes"] is not None:
                frames = session.frame_buffer.push(message["bytes"])

                for frame in frames:
                    event = session.vad.process_frame(frame)

                    if event == "speech_started":
                        await _handle_speech_started(session, websocket)
                    elif event == "speech_ended":
                        asyncio.create_task(_handle_speech_ended(session, websocket))

                    if session.vad.is_speaking:
                        session.utterance_buffer.add(frame)

            elif "text" in message and message["text"] is not None:
                logger.info(f"[{session.session_id}] Control: {message['text']}")

    except WebSocketDisconnect:
        logger.info(f"[{session.session_id}] Client disconnected")
    except Exception as e:
        logger.error(f"[{session.session_id}] WebSocket error: {e}")
    finally:
        session_manager.end_session(session.session_id)
        logger.info(f"[{session.session_id}] Session cleaned up")
