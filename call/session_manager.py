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