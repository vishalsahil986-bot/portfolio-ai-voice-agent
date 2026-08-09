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