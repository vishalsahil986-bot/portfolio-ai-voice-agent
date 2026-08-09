from fastapi import APIRouter, WebSocket, WebSocketDisconnect
 
from call.call_state_machine import CallState
from call.session_manager import session_manager
from utils.logger import get_logger
 
logger = get_logger(__name__)
router = APIRouter()

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
                audio_chunk = message["bytes"]
                logger.info(f"[{session.session_id}] received {len(audio_chunk)} bytes of audio")
                
                await websocket.send_json({"type": "audio_ack", "bytes_received": len(audio_chunk)})
 
            elif "text" in message and message["text"] is not None:
                # Simple control messages from the client, e.g. {"type": "end_turn"}
                logger.info(f"[{session.session_id}] control message: {message['text']}")
 
    except WebSocketDisconnect:
        logger.info(f"[{session.session_id}] client disconnected")
    finally:
        session_manager.end_session(session.session_id)