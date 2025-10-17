"""
Model manager - Handles initialization and lifecycle of all ML models
"""
import logging
from typing import Optional

from app.services.demucs_service import DemucsService
from app.services.omnizart_service import OmnizartService
from app.services.sheet_music_service import SheetMusicService

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages all ML models and services"""
    
    def __init__(self):
        self.demucs_service: Optional[DemucsService] = None
        self.omnizart_service: Optional[OmnizartService] = None
        self.sheet_music_service: Optional[SheetMusicService] = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize all services"""
        try:
            logger.info("Initializing ModelManager...")
            
            # Initialize Demucs service
            logger.info("Initializing Demucs service...")
            self.demucs_service = DemucsService()
            await self.demucs_service.initialize()
            
            # Initialize Omnizart service
            logger.info("Initializing Omnizart service...")
            self.omnizart_service = OmnizartService()
            await self.omnizart_service.initialize()
            
            # Initialize Sheet Music service
            logger.info("Initializing Sheet Music service...")
            self.sheet_music_service = SheetMusicService()
            
            self.initialized = True
            logger.info("ModelManager initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize ModelManager: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup all services"""
        logger.info("Cleaning up ModelManager...")
        
        if self.demucs_service:
            await self.demucs_service.cleanup()
        
        if self.omnizart_service:
            await self.omnizart_service.cleanup()
        
        self.initialized = False
        logger.info("ModelManager cleanup complete")
    
    def is_ready(self) -> bool:
        """Check if all services are ready"""
        return (
            self.initialized and
            self.demucs_service is not None and
            self.omnizart_service is not None and
            self.sheet_music_service is not None
        )
