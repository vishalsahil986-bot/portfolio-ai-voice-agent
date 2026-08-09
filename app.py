from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from api.health_routes import router as health_router
from api.websocket_routes import router as websocket_router
from utils.logger import get_logger
 
logger = get_logger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(title="AI Voice Agent", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
 
    app.include_router(health_router)
    app.include_router(websocket_router)
 