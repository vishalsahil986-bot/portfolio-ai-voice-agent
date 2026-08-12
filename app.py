from fastapi import FastAPI
import asyncio 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

    @app.on_event("startup")
    async def on_startup():
        logger.info("AI Voice Agent starting up...")
        # Eagerly load all models in background at startup
        asyncio.create_task(_warmup())

    async def _warmup():
        """Load all models at startup so first user request is instant."""
        import asyncio
        from audio.stt_whisper import whisper_stt
        from rag.embeddings import embedding_service
        from rag.vector_store import vector_store
        from rag.retriever import retriever

        logger.info("Warming up models...")
        # Load Whisper
        await asyncio.to_thread(whisper_stt._ensure_loaded)
        # Load embeddings
        await asyncio.to_thread(embedding_service._ensure_loaded)
        # Connect Pinecone
        await asyncio.to_thread(vector_store._ensure_index)
        logger.info("All models warmed up ✅")

    return app


app = create_app()