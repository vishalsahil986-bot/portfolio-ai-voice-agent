from typing import List
 
from google import genai
from google.genai import types
from google.genai.errors import APIError
 
from config.settings import settings
from llm.prompt_builder import SYSTEM_INSTRUCTION, build_contents
from utils.logger import get_logger
 
logger = get_logger(__name__)