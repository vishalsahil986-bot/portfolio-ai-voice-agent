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


async def _handle_speech_started(session: Session) -> None:
    if session.state_machine.state == CallState.SPEAKING:

        session.state_machine.interrupt()
        session.interrupted = True
    session.utterance_buffer.reset()


async def _handle_speech_ended(session: Session, websocket: WebSocket) -> None:
    audio = session.utterance_buffer.get_audio()
    session.utterance_buffer.reset()

    if not audio:
        return

    session.interrupted = False
    session.state_machine.transition(CallState.THINKING)

    text = await asyncio.to_thread(whisper_stt.transcribe, audio)

    if not text or len(text.strip()) < 3:  # too short = noise
        session.state_machine.transition(CallState.LISTENING)
        return

    # Filter common Whisper hallucinations on silence
    JUNK_PHRASES = [". . .", "...", "you", "bye", "thanks", "thank you"]
    if text.strip().lower() in JUNK_PHRASES:
        logger.info(f"[{session.session_id}] filtered junk transcription: '{text}'")
        session.state_machine.transition(CallState.LISTENING)
        return


    if not text:
        session.state_machine.transition(CallState.LISTENING)
        return

    await websocket.send_json({"type": "transcript", "text": text})

    #  Phase 5: increment message count + build memory context 
    msg_count = await memory_manager.increment_message_count(session.session_id)

    #  Phase 4: RAG retrieval 
    context = await asyncio.to_thread(retriever.retrieve, text)

    #  Build full Gemini context (summaries + recent turns + RAG) 
    contents = await build_gemini_context(
        session_id=session.session_id,
        conversation_history=session.conversation_history,
        new_user_text=text,
        retrieved_context=context,
        message_count=msg_count,
    )

    #  Gemini LLM call 
    try:
        reply_text = await asyncio.to_thread(
            gemini_service.generate_reply_from_contents, contents
        )
    except AllGeminiKeysExhausted:
        logger.error(f"[{session.session_id}] all Gemini keys exhausted, skipping this turn")
        session.state_machine.transition(CallState.LISTENING)
        return
    except GeminiApiError as e:
        logger.error(f"[{session.session_id}] Gemini call failed: {e}")
        session.state_machine.transition(CallState.LISTENING)
        return

    if not reply_text:
        session.state_machine.transition(CallState.LISTENING)
        return

    #  Save turn to in-RAM history 
    session.conversation_history.append({"role": "user", "text": text})
    session.conversation_history.append({"role": "model", "text": reply_text})

    #  Phase 5: fire background summarization 
    await summarize_exchange_in_background(
        session_id=session.session_id,
        user_text=text,
        bot_text=reply_text,
        message_count=msg_count,
    )

    session.state_machine.transition(CallState.SPEAKING)

    #  ElevenLabs TTS 
    try:
        reply_audio = await asyncio.to_thread(voice_manager.synthesize, reply_text)
    except AllElevenLabsKeysExhausted:
        logger.error(f"[{session.session_id}] all ElevenLabs accounts exhausted, skipping TTS")
        session.state_machine.transition(CallState.LISTENING)
        return
    except ApiError as e:
        logger.error(f"[{session.session_id}] ElevenLabs TTS failed: {e}")
        session.state_machine.transition(CallState.LISTENING)
        return

    if session.interrupted:
        logger.info(f"[{session.session_id}] reply discarded, user interrupted during synthesis")
    else:
        await websocket.send_json({"type": "reply_text", "text": reply_text})
        await websocket.send_bytes(reply_audio)

    if session.state_machine.state == CallState.SPEAKING:
        session.state_machine.transition(CallState.LISTENING)


@router.websocket("/ws/call")
async def call_websocket(websocket: WebSocket):
    await websocket.accept()
    session = session_manager.create_session()

    await websocket.send_json({
        "type": "session_started",
        "session_id": session.session_id,
    })

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
                        await _handle_speech_started(session)
                    elif event == "speech_ended":
                        await _handle_speech_ended(session, websocket)

                    if session.vad.is_speaking:
                        session.utterance_buffer.add(frame)

            elif "text" in message and message["text"] is not None:
                logger.info(f"[{session.session_id}] control message: {message['text']}")

    except WebSocketDisconnect:
        logger.info(f"[{session.session_id}] client disconnected")
    finally:
        session_manager.end_session(session.session_id)