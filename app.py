"""
app.py

FastAPI application factory.
Handles startup (model warmup + MongoDB TTL index creation) and shutdown.
"""

import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.health_routes import router as health_router
from api.websocket_routes import router as websocket_router
from utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="AI Voice Agent — Sada", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(websocket_router)
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

    @app.on_event("startup")
    async def on_startup():
        logger.info("AI Voice Agent (Sada) starting up...")
        # Initialize MongoDB TTL index and warm up models concurrently
        asyncio.create_task(_init_memory())
        asyncio.create_task(_warmup_models())

    @app.on_event("shutdown")
    async def on_shutdown():
        from memory.memory_manager import memory_manager
        await memory_manager.close()
        logger.info("AI Voice Agent shut down cleanly")

    return app


async def _init_memory() -> None:
    """Create MongoDB TTL index on startup."""
    try:
        from memory.memory_manager import memory_manager
        await memory_manager.initialize()
        logger.info("Memory manager initialized ✅")
    except Exception as e:
        logger.error(f"Memory manager initialization failed: {e}")


async def _warmup_models() -> None:
    logger.info("Model warmup skipped — lazy loading enabled")


app = create_app()
