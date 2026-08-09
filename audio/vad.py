import collections
from typing import Optional
 
import webrtcvad
 
from config.settings import settings
from utils.logger import get_logger
 
logger = get_logger(__name__)