import uuid
from dataclasses import dataclass, field
from typing import Dict
 
from call.call_state_machine import CallStateMachine
from utils.logger import get_logger
 
logger = get_logger(__name__)

 
@dataclass
class Session:
    session_id: str
    state_machine: CallStateMachine = field(init=False)
 
    def __post_init__(self):
        self.state_machine = CallStateMachine(self.session_id)

class SessionManager:
    """In-memory session registry. Fine for Phase 1; swap for Redis in production (see docs)."""
 
    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create_session(self) -> Session:
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id)
        self._sessions[session_id] = session
        logger.info(f"Session created: {session_id}")
        return session
 
    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)
 
    def end_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Session ended: {session_id}")
 
 
# One shared instance for the whole app.
session_manager = SessionManager()