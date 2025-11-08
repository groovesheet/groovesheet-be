"""
Test worker processing pipeline without Docker
Run this directly with your local Python environment
"""
import os
import sys
import logging
from pathlib import Path

# Get the script directory and set up paths
script_dir = Path(__file__).parent.absolute()
backend_dir = script_dir / "backend"
annoteator_dir = script_dir / "AnNOTEator"
demucs_dir = script_dir / "demucs"

# Add paths (same as worker)
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(annoteator_dir))
sys.path.insert(0, str(demucs_dir))

print(f"Python paths set:")
print(f"  Backend: {backend_dir}")
print(f"  AnNOTEator: {annoteator_dir}")
print(f"  Demucs: {demucs_dir}")
print()

# Setup logging (same as worker)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import the same service the worker uses
from app.services.annoteator_service import AnNOTEatorService

def test_processing(audio_file: str, output_dir: str = "./test_output"):
    """
    Test the exact same processing pipeline as the worker
    
    Args:
        audio_file: Path to your test audio file
        output_dir: Where to save output (default: ./test_output)
    """
    logger.info("=" * 70)
    logger.info("TESTING WORKER PROCESSING PIPELINE")
    logger.info("=" * 70)
    logger.info(f"Audio file: {audio_file}")
    logger.info(f"Output directory: {output_dir}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Initialize service (same as worker)
        annoteator = AnNOTEatorService(output_dir=output_dir)
        logger.info("✓ AnNOTEatorService initialized")
        
        # Process audio (same parameters as worker)
        logger.info("")
        logger.info("Starting transcription...")
        result_path, result_metadata = annoteator.transcribe_audio(
            audio_path=audio_file,
            output_name="test_output",
            song_title=os.path.basename(audio_file),
            use_demucs=True
        )
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ PROCESSING COMPLETE!")
        logger.info("=" * 70)
        logger.info(f"Output: {result_path}")
        logger.info(f"Metadata: {result_metadata}")
        
        return True
        
    except Exception as e:
        logger.error("")
        logger.error("=" * 70)
        logger.error("❌ PROCESSING FAILED!")
        logger.error("=" * 70)
        logger.error(f"Error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Test with your audio file - update this path as needed
    test_audio = script_dir / "Nirvana - Smells Like Teen Spirit (Official Music Video).mp3"
    
    # Alternative: use command line argument
    if len(sys.argv) > 1:
        test_audio = Path(sys.argv[1])
    
    if not test_audio.exists():
        logger.error(f"Test audio file not found: {test_audio}")
        logger.error("Usage: python test_worker_processing.py [audio_file.mp3]")
        logger.error(f"Or update the 'test_audio' path in this script")
        sys.exit(1)
    
    success = test_processing(str(test_audio))
    sys.exit(0 if success else 1)
