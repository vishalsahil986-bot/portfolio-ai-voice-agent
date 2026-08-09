import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from audio.stt_whisper import whisper_stt
from call.call_state_machine import CallState
from call.session_manager import Session, session_manager
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

    if not text:
        session.state_machine.transition(CallState.LISTENING)
        return

    await websocket.send_json({"type": "transcript", "text": text})

    reply_text = f"You said: {text}"

    session.state_machine.transition(CallState.SPEAKING)

    try:
        reply_audio = await asyncio.to_thread(voice_manager.synthesize, reply_text)
    except AllElevenLabsKeysExhausted:
        logger.error(f"[{session.session_id}] all ElevenLabs accounts exhausted, skipping TTS")
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