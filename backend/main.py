"""
DrumScore Backend Server
Main FastAPI application entry point
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Set environment variables for Windows multiprocessing compatibility
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.routes import transcription, health, annoteator
from app.services.model_manager import ModelManager

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown"""
    # Startup
    logger.info("Starting DrumScore Backend Server...")
    
    # Initialize directories
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    os.makedirs(settings.MODELS_DIR, exist_ok=True)
    
    # Initialize model manager
    logger.info("Initializing models...")
    model_manager = ModelManager()
    await model_manager.initialize()
    app.state.model_manager = model_manager
    
    logger.info("Server started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down server...")
    if hasattr(app.state, 'model_manager'):
        await app.state.model_manager.cleanup()
    logger.info("Server shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="DrumScore Backend API",
    description="Backend service for drum transcription from audio files",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for serving generated PDFs
if os.path.exists(settings.OUTPUT_DIR):
    app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(transcription.router, prefix="/api/v1", tags=["Transcription"])
app.include_router(annoteator.router, tags=["AnNOTEator"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "DrumScore Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
