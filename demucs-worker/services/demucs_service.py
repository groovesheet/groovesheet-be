"""
Demucs Service - Handles audio source separation using Demucs
"""
import os
import sys
import tempfile
import logging
import time
from pathlib import Path
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
import warnings

# ---------------------------
# Load environment variables from .env file (if exists)
# ---------------------------
try:
    from dotenv import load_dotenv
    # Load .env from project root (demucs-worker/.env) or current directory
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try parent directory (project root)
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, skip
    pass

# Add demucs library to path if it exists in library directory
# In Docker: /app/services/demucs_service.py -> /app/library/demucs
# Locally: demucs-worker/services/demucs_service.py -> library/demucs
if (Path(__file__).parent.parent / "library" / "demucs").exists():
    # Docker container structure: /app/services -> /app/library/demucs
    DEMUCS_LIB_PATH = Path(__file__).parent.parent / "library" / "demucs"
else:
    # Local development structure: demucs-worker/services -> library/demucs
    DEMUCS_LIB_PATH = Path(__file__).parent.parent.parent / "library" / "demucs"
    if DEMUCS_LIB_PATH.exists():
        sys.path.insert(0, str(DEMUCS_LIB_PATH))

# ---------------------------
# Configuration
# ---------------------------


@dataclass
class DemucsSettings:
    """Demucs service configuration loaded from environment variables."""
    demucs_device: str = os.getenv("DEMUCS_DEVICE", "cpu")
    demucs_num_workers: int = int(os.getenv("DEMUCS_NUM_WORKERS", "1"))
    demucs_mode: str = os.getenv("DEMUCS_MODE", "speed")  # 'speed' or 'performance'
    demucs_model_dir: str = os.getenv("DEMUCS_MODEL_DIR", "")
    omp_num_threads: int = int(os.getenv("OMP_NUM_THREADS", "4"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def __post_init__(self):
        """Apply environment variable settings to os.environ for libraries."""
        os.environ["OMP_NUM_THREADS"] = str(self.omp_num_threads)


# Initialize settings and apply to environment
demucs_settings = DemucsSettings()

# Suppress warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# Import heavy libraries at MODULE level (once per container startup, not per job)
logger.info("Loading Demucs libraries (one-time startup cost)...")
import librosa
import soundfile as sf
logger.info("✓ Demucs libraries loaded")


class DemucsService:
    """Service for separating audio sources using Demucs"""
    
    def __init__(self, output_dir: str = None, model_dir: Optional[str] = None):
        """
        Initialize Demucs service
        
        Args:
            output_dir: Directory to save output files
            model_dir: Optional directory containing Demucs model files (.th files)
        """
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "groovesheet" / "demucs"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine model directory
        if model_dir:
            self.model_dir = Path(model_dir)
        elif demucs_settings.demucs_model_dir:
            self.model_dir = Path(demucs_settings.demucs_model_dir)
        elif (Path(__file__).parent.parent.parent / "library" / "AnNOTEator" / "inference" / "pretrained_models" / "demucs").exists():
            # Use AnNOTEator's demucs models if available
            self.model_dir = Path(__file__).parent.parent.parent / "library" / "AnNOTEator" / "inference" / "pretrained_models" / "demucs"
        else:
            # Default: use demucs package's default model location
            self.model_dir = None
        
        logger.info(f"Demucs model directory: {self.model_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Device: {demucs_settings.demucs_device}")
        logger.info(f"Mode: {demucs_settings.demucs_mode}")
        logger.info(f"Workers: {demucs_settings.demucs_num_workers}")
    
    def separate_audio(
        self,
        audio_path: str,
        output_name: Optional[str] = None,
        extract_drums_only: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Tuple[str, Dict]:
        """
        Separate audio file into sources using Demucs
        
        Args:
            audio_path: Path to audio file (mp3, wav, etc.)
            output_name: Optional output filename (without extension)
            extract_drums_only: If True, only return drums track. If False, return all sources.
        
        Returns:
            Tuple of (output_path, metadata)
        """
        logger.info("=" * 70)
        logger.info("ENTERED separate_audio() method")
        logger.info("=" * 70)
        sys.stdout.flush()
        sys.stderr.flush()
        
        import uuid
        if not output_name:
            output_name = f"demucs_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info("=" * 70)
            logger.info(f"STARTING DEMUCS SEPARATION PIPELINE")
            logger.info("=" * 70)
            logger.info(f"Input audio: {audio_path}")
            logger.info(f"Extract drums only: {extract_drums_only}")
            logger.info(f"Mode: {demucs_settings.demucs_mode}")
            
            # Import demucs
            from demucs import pretrained, apply, audio
            
            # Determine model directory
            model_repo = Path(self.model_dir) if self.model_dir else None
            
            # Load model(s) based on mode
            if demucs_settings.demucs_mode == 'speed':
                logger.info("Loading Demucs model (speed mode - single model)...")
                model = pretrained.get_model(name='83fc094f', repo=model_repo)
                model = apply.BagOfModels([model])
                logger.info("✓ Speed mode: processing time typically 1-2 mins.")
            elif demucs_settings.demucs_mode == 'performance':
                logger.info("Loading Demucs models (performance mode - bag of 4 models)...")
                model_1 = pretrained.get_model(name='14fc6a69', repo=model_repo)
                model_2 = pretrained.get_model(name='464b36d7', repo=model_repo)
                model_3 = pretrained.get_model(name='7fd6ef75', repo=model_repo)
                model_4 = pretrained.get_model(name='83fc094f', repo=model_repo)
                model = apply.BagOfModels([model_1, model_2, model_3, model_4])
                logger.info("✓ Performance mode: bag of 4 models, expect 4 progress bars (4-6 mins).")
            else:
                raise ValueError(f"Invalid mode: {demucs_settings.demucs_mode}. Must be 'speed' or 'performance'")
            
            # Load audio
            logger.info("Loading audio file...")
            wav = audio.AudioFile(audio_path).read(
                streams=0,
                samplerate=model.samplerate,
                channels=model.audio_channels
            )
            
            # Normalize audio
            ref = wav.mean(0)
            wav = (wav - ref.mean()) / ref.std()
            
            # Apply model
            logger.info(f"Applying Demucs model (workers={demucs_settings.demucs_num_workers})...")
            if progress_callback:
                progress_callback(30, "Applying Demucs separation model")
            
            sources = apply.apply_model(
                model, wav[None],
                device=demucs_settings.demucs_device,
                shifts=1,
                split=True,
                overlap=0.25,
                progress=True,
                num_workers=demucs_settings.demucs_num_workers
            )[0]
            
            # Denormalize
            sources = sources * ref.std() + ref.mean()
            
            # Extract drums (index 0) or all sources
            if extract_drums_only:
                drum_track = sources[0]
                sample_rate = model.samplerate
                drum_mono = librosa.to_mono(drum_track)
                
                # Save drums only
                output_path = self.output_dir / f"{output_name}_drums.wav"
                sf.write(str(output_path), drum_mono, sample_rate)
                
                logger.info(f"✅ Demucs separation completed!")
                logger.info(f"  - Output: {output_path}")
                logger.info(f"  - Sample rate: {sample_rate} Hz")
                
                metadata = {
                    "output_type": "drums_only",
                    "sample_rate": sample_rate,
                    "mode": demucs_settings.demucs_mode,
                    "device": demucs_settings.demucs_device
                }
                
                return str(output_path), metadata
            else:
                # Save all sources (drums, bass, other, vocals)
                output_files = {}
                source_names = ["drums", "bass", "other", "vocals"]
                
                for idx, source_name in enumerate(source_names):
                    source_mono = librosa.to_mono(sources[idx])
                    output_path = self.output_dir / f"{output_name}_{source_name}.wav"
                    sf.write(str(output_path), source_mono, model.samplerate)
                    output_files[source_name] = str(output_path)
                
                logger.info(f"✅ Demucs separation completed!")
                logger.info(f"  - Outputs: {len(output_files)} files")
                for name, path in output_files.items():
                    logger.info(f"    - {name}: {path}")
                
                metadata = {
                    "output_type": "all_sources",
                    "output_files": output_files,
                    "sample_rate": model.samplerate,
                    "mode": demucs_settings.demucs_mode,
                    "device": demucs_settings.demucs_device
                }
                
                return str(output_files["drums"]), metadata
                
        except Exception as e:
            logger.error(f"Error during Demucs separation: {e}", exc_info=True)
            raise
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up temporary files older than max_age_hours"""
        current_time = time.time()
        
        cleaned_count = 0
        for file in self.output_dir.glob("demucs_*.wav"):
            file_age_hours = (current_time - file.stat().st_mtime) / 3600
            if file_age_hours > max_age_hours:
                file.unlink()
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old files")
        
        return cleaned_count


