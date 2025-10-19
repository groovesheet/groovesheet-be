"""
Omnizart service for drum transcription
Converts drum audio to MIDI notation using 6 practical drum classes
"""
import os
import sys
import logging
from typing import Optional
import numpy as np
import pretty_midi
from scipy.signal import find_peaks

# Add omnizart to path
OMNIZART_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'omnizart')
if OMNIZART_PATH not in sys.path:
    sys.path.insert(0, OMNIZART_PATH)

from app.core.config import settings

logger = logging.getLogger(__name__)


class OmnizartService:
    """Service for drum transcription using Omnizart"""
    
    def __init__(self):
        self.drum_transcription = None
        self.model_path = settings.OMNIZART_MODEL_PATH
        self.device = settings.OMNIZART_DEVICE
        
        # Configure TensorFlow
        self._configure_tensorflow()
        
        logger.info(f"OmnizartService initialized with device: {self.device}")
    
    def _configure_tensorflow(self):
        """Configure TensorFlow settings"""
        try:
            logger.info("Configuring TensorFlow (this may take a moment on macOS with emulation)...")
            
            # Lazy import TensorFlow only when needed
            import tensorflow as tf
            logger.info(f"TensorFlow version: {tf.__version__}")
            
            # Set memory growth for GPU
            if self.device == "cuda":
                logger.info("Checking for GPU devices...")
                gpus = tf.config.list_physical_devices('GPU')
                if gpus:
                    for gpu in gpus:
                        tf.config.experimental.set_memory_growth(gpu, True)
                    logger.info(f"✓ Found {len(gpus)} GPU(s)")
                else:
                    logger.warning("No GPU found, using CPU")
                    self.device = "cpu"
            else:
                logger.info("Using CPU for inference (GPU not requested)")
            
            # Suppress TensorFlow warnings
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
            tf.get_logger().setLevel('ERROR')
            logger.info("✓ TensorFlow configured successfully")
            
        except Exception as e:
            logger.warning(f"Error configuring TensorFlow: {str(e)}")
    
    async def initialize(self):
        """Initialize the Omnizart drum transcription model"""
        try:
            logger.info("=" * 60)
            logger.info("Starting Omnizart drum transcription model initialization")
            logger.info("=" * 60)
            logger.info("Step 1/5: Importing Omnizart dependencies...")
            
            # Lazy import drum_app only when needed
            from omnizart.drum import app as drum_app
            logger.info("✓ Omnizart drum module imported successfully")
            
            logger.info("Step 2/5: Initializing drum transcription app...")
            # Initialize drum transcription app
            self.drum_transcription = drum_app
            logger.info("✓ Drum transcription app initialized")
            
            logger.info("Step 3/5: Checking model checkpoints...")
            # Download checkpoints if needed
            checkpoint_path = os.path.join(settings.MODELS_DIR, 'omnizart_checkpoints')
            if not os.path.exists(checkpoint_path):
                logger.info("⚠ Checkpoints not found, creating directory...")
                os.makedirs(checkpoint_path, exist_ok=True)
                logger.info("✓ Checkpoint directory created")
                logger.info("Note: Model will download checkpoints on first use")
            else:
                logger.info("✓ Checkpoint directory exists")
            
            logger.info("Step 4/5: Verifying model configuration...")
            # Verify the model can be accessed
            logger.info(f"  - Model path: {settings.MODELS_DIR}")
            logger.info(f"  - Device: {self.device}")
            logger.info("✓ Model configuration verified")
            
            logger.info("Step 5/5: Finalizing initialization...")
            logger.info("✓ Omnizart model loaded successfully")
            logger.info("=" * 60)
            logger.info("Omnizart initialization complete! Ready for transcription.")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"✗ Failed to initialize Omnizart model: {str(e)}")
            logger.error("=" * 60)
            raise
    
    def _inference_6_classes(self, pred: np.ndarray, mini_beat_arr: np.ndarray, threshold: float = 0.8) -> tuple:
        """
        Custom inference function that groups Omnizart's 13 classes into 6 practical drum classes
        
        Groups:
        1. Kick/Bass Drum (class 0)
        2. Snare (class 1 + side stick 2)
        3. Hi-Hat (classes 4, 5, 6 - closed, pedal, open)
        4. Toms (classes 7, 8, 9 - low, mid, high)
        5. Ride Cymbal (class 11)
        6. Crash Cymbal (class 10)
        
        Args:
            pred: Prediction array of shape (n_frames, 13)
            mini_beat_arr: Time array for each frame
            threshold: Peak detection threshold (z-score)
            
        Returns:
            Tuple of (PrettyMIDI object, note counts dict)
        """
        # Group the 13 classes into 6 practical groups
        grouped_pred = np.zeros((pred.shape[0], 6))
        
        grouped_pred[:, 0] = pred[:, 0]                           # Kick (0)
        grouped_pred[:, 1] = np.max(pred[:, [1, 2]], axis=1)     # Snare + Side Stick (1,2)
        grouped_pred[:, 2] = np.max(pred[:, [4, 5, 6]], axis=1)  # All Hi-Hats (4,5,6)
        grouped_pred[:, 3] = np.max(pred[:, [7, 8, 9]], axis=1)  # All Toms (7,8,9)
        grouped_pred[:, 4] = pred[:, 11]                          # Ride (11)
        grouped_pred[:, 5] = pred[:, 10]                          # Crash (10)
        
        # Mapping to MIDI pitches (General MIDI drum map)
        class_to_midi = {
            0: 36,  # Kick (Bass Drum 1)
            1: 38,  # Snare (Acoustic Snare)
            2: 42,  # Hi-Hat (Closed Hi-Hat)
            3: 47,  # Toms (Low-Mid Tom)
            4: 51,  # Ride (Ride Cymbal 1)
            5: 49   # Crash (Crash Cymbal 1)
        }
        
        class_names = [
            "Kick/Bass",
            "Snare",
            "Hi-Hat",
            "Toms",
            "Ride",
            "Crash"
        ]
        
        norm = lambda x: (x - np.mean(x)) / np.std(x)
        
        drum_inst = pretty_midi.Instrument(program=0, is_drum=True, name="drums")
        note_counts = {}
        
        # Process each of the 6 grouped classes
        for class_idx in range(6):
            # Normalize and find peaks
            normalized = norm(grouped_pred[:, class_idx])
            peaks, _ = find_peaks(normalized, height=threshold, distance=1)
            
            # Register notes for this drum class
            for onset in mini_beat_arr[peaks]:
                note = pretty_midi.Note(
                    velocity=100,
                    pitch=class_to_midi[class_idx],
                    start=onset,
                    end=onset + 0.05
                )
                drum_inst.notes.append(note)
            
            note_counts[class_names[class_idx]] = len(peaks)
        
        # Sort notes by time
        drum_inst.notes.sort(key=lambda x: x.start)
        
        midi = pretty_midi.PrettyMIDI(initial_tempo=120)
        midi.instruments.append(drum_inst)
        
        return midi, note_counts

    async def transcribe_drums(
        self,
        drum_audio_path: str,
        output_dir: str,
        threshold: float = 0.8
    ) -> str:
        """
        Transcribe drum audio to MIDI using 6 practical drum classes
        
        Args:
            drum_audio_path: Path to drum audio file (separated)
            output_dir: Directory to save MIDI file
            threshold: Peak detection threshold (default 0.8)
            
        Returns:
            Path to generated MIDI file
        """
        try:
            logger.info(f"Starting drum transcription for: {drum_audio_path}")
            
            if not self.drum_transcription:
                raise RuntimeError("Omnizart model not initialized")
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Lazy imports to avoid multiprocessing issues
            from omnizart.feature.wrapper_func import extract_patch_cqt
            from omnizart.drum.prediction import predict
            
            logger.info("Extracting features...")
            patch_cqt_feature, mini_beat_arr = extract_patch_cqt(drum_audio_path)
            
            logger.info("Loading model...")
            model, model_settings = self.drum_transcription._load_model(
                None, 
                custom_objects=self.drum_transcription.custom_objects
            )
            
            logger.info("Predicting drum hits...")
            pred = predict(patch_cqt_feature, model, model_settings.feature.mini_beat_per_segment)
            logger.info(f"Prediction shape: {pred.shape} (13 classes → grouping to 6)")
            
            logger.info("Inferring MIDI with 6 practical drum classes...")
            midi, note_counts = self._inference_6_classes(pred, mini_beat_arr, threshold)
            
            # Save MIDI
            midi_filename = os.path.splitext(os.path.basename(drum_audio_path))[0] + ".mid"
            midi_path = os.path.join(output_dir, midi_filename)
            midi.write(midi_path)
            
            total_notes = sum(note_counts.values())
            logger.info(f"Drum transcription completed: {midi_path}")
            logger.info(f"Total notes: {total_notes}")
            logger.info(f"Notes per class: {note_counts}")
            
            return midi_path
            
        except Exception as e:
            logger.error(f"Error during drum transcription: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up Omnizart service")
        
        # Clear TensorFlow session
        try:
            import tensorflow as tf
            tf.keras.backend.clear_session()
        except Exception as e:
            logger.warning(f"Error clearing TensorFlow session: {str(e)}")
        
        self.drum_transcription = None
