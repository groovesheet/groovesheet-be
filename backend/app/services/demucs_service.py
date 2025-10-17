"""
Demucs service for audio source separation
Separates drum track from full music mix
"""
import os
import sys
import logging
import torch
from pathlib import Path
from typing import Optional

# Add demucs to path
DEMUCS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'demucs')
if DEMUCS_PATH not in sys.path:
    sys.path.insert(0, DEMUCS_PATH)

from demucs.api import Separator, save_audio
from demucs.pretrained import get_model

from app.core.config import settings

logger = logging.getLogger(__name__)


class DemucsService:
    """Service for separating drum tracks using Demucs"""
    
    def __init__(self):
        self.separator: Optional[Separator] = None
        self.model_name = settings.DEMUCS_MODEL
        self.device = settings.DEMUCS_DEVICE
        
        # Check if CUDA is available
        if self.device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA not available, falling back to CPU")
            self.device = "cpu"
        
        logger.info(f"DemucsService initialized with device: {self.device}")
    
    async def initialize(self):
        """Initialize the Demucs model"""
        try:
            logger.info(f"Loading Demucs model: {self.model_name}")
            
            self.separator = Separator(
                model=self.model_name,
                device=self.device,
                shifts=settings.DEMUCS_SHIFTS,
                overlap=settings.DEMUCS_OVERLAP,
                split=True,
                progress=False
            )
            
            logger.info("Demucs model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Demucs model: {str(e)}")
            raise
    
    async def separate_drums(
        self, 
        input_audio_path: str, 
        output_dir: str
    ) -> str:
        """
        Separate drum track from audio file
        
        Args:
            input_audio_path: Path to input audio file
            output_dir: Directory to save separated drum track
            
        Returns:
            Path to separated drum audio file
        """
        try:
            logger.info(f"Starting drum separation for: {input_audio_path}")
            
            if not self.separator:
                raise RuntimeError("Demucs model not initialized")
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Load and separate audio
            input_path = Path(input_audio_path)
            
            # Perform separation
            origin, separated = self.separator.separate_audio_file(str(input_path))
            
            # Extract drum track
            # Demucs separates into: drums, bass, other, vocals
            if 'drums' not in separated:
                raise ValueError("Drums track not found in separated output")
            
            drums = separated['drums']
            
            # Save drum track
            drum_output_path = os.path.join(output_dir, "drums.wav")
            save_audio(
                drums,
                drum_output_path,
                samplerate=self.separator.samplerate,
                bitrate=320,
                clip='rescale',
                as_float=False,
                bits_per_sample=24
            )
            
            logger.info(f"Drum separation completed: {drum_output_path}")
            return drum_output_path
            
        except Exception as e:
            logger.error(f"Error during drum separation: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up Demucs service")
        if self.separator:
            # Clear CUDA cache if using GPU
            if self.device == "cuda":
                torch.cuda.empty_cache()
        self.separator = None
