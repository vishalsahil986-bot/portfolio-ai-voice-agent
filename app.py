from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from api.health_routes import router as health_router
from api.websocket_routes import router as websocket_router
from utils.logger import get_logger
 
logger = get_logger(__name__)
 