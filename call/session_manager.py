import uuid
from dataclasses import dataclass, field
from typing import Dict
 
from call.call_state_machine import CallStateMachine
from utils.logger import get_logger
 
logger = get_logger(__name__)