"""
AnNOTEator Service - Handles drum transcription using AnNOTEator
"""
import os
import sys
import tempfile
import uuid
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict
import warnings

# Add AnNOTEator to path
ANNOTEATOR_PATH = Path(__file__).parent.parent.parent.parent / "AnNOTEator"
sys.path.insert(0, str(ANNOTEATOR_PATH))

# Suppress warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

logger = logging.getLogger(__name__)


class AnNOTEatorService:
    """Service for transcribing drums using AnNOTEator"""
    
    def __init__(self, output_dir: str = None):
        """
        Initialize AnNOTEator service
        
        Args:
            output_dir: Directory to save output files
        """
        self.annoteator_path = ANNOTEATOR_PATH
        self.model_path = ANNOTEATOR_PATH / "inference" / "pretrained_models" / "annoteators" / "complete_network.h5"
        
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(tempfile.gettempdir()) / "groovesheet"
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"AnNOTEator path: {self.annoteator_path}")
        logger.info(f"Model path: {self.model_path}")
        logger.info(f"Output directory: {self.output_dir}")
        
        if not self.model_path.exists():
            raise FileNotFoundError(f"AnNOTEator model not found at {self.model_path}")
    
    def transcribe_audio(
        self, 
        audio_path: str,
        output_name: Optional[str] = None,
        song_title: str = "Drum Transcription",
        use_demucs: bool = True
    ) -> Tuple[str, Dict]:
        """
        Transcribe audio file to MusicXML using AnNOTEator
        
        Args:
            audio_path: Path to audio file (mp3, wav, etc.)
            output_name: Optional output filename (without extension)
            song_title: Title for the sheet music
            use_demucs: Whether to process through Demucs first (recommended: True)
        
        Returns:
            Tuple of (musicxml_path, metadata)
        """
        # Import here to avoid pytube import issues
        import librosa
        import pandas as pd
        import soundfile as sf
        
        # Import these after fixing the pytube issue
        try:
            from inference.input_transform import drum_to_frame
            from inference.prediction import predict_drumhit
            from inference.transcriber import drum_transcriber
        except ImportError as e:
            logger.error(f"Failed to import AnNOTEator modules: {e}")
            raise ImportError(f"AnNOTEator dependencies not available: {e}")
        
        # Generate output filename
        if not output_name:
            output_name = f"transcription_{uuid.uuid4().hex[:8]}"
        
        output_musicxml = self.output_dir / f"{output_name}.musicxml"
        demucs_output_path = None
        
        try:
            logger.info("=" * 70)
            logger.info(f"STARTING DRUM TRANSCRIPTION PIPELINE")
            logger.info("=" * 70)
            logger.info(f"Input audio: {audio_path}")
            logger.info(f"Song title: {song_title}")
            logger.info(f"Use Demucs: {use_demucs}")
            
            # Step 1: Process through Demucs (extract drums)
            if use_demucs:
                logger.info("")
                logger.info("STEP 1/4: DEMUCS DRUM EXTRACTION")
                logger.info("-" * 70)
                logger.info("Processing audio through Demucs to isolate drums...")
                logger.info("This step removes vocals, bass, and other instruments.")
                logger.info("Expected time: 30-60 seconds for a 3-4 minute song")
                logger.info("")
                logger.info("📊 Demucs uses a bag of 4 models (htdemucs):")
                logger.info("   Model 1/4: Starting...")
                
                try:
                    from inference.input_transform import drum_extraction
                    import time
                    import sys
                    
                    # Force stdout flush for Docker logs
                    sys.stdout.flush()
                    sys.stderr.flush()
                    
                    start_time = time.time()
                    
                    # Use Demucs to extract drums (with progress=True in apply_model)
                    # Using 'speed' mode (1 model) instead of 'performance' (4 models) to reduce memory usage
                    # Performance mode requires 16GB+ RAM, speed mode needs only 4GB
                    logger.info("🎵 Loading and processing audio file...")
                    logger.info("⏳ Calling drum_extraction (this may take 1-2 minutes)...")
                    sys.stdout.flush()
                    sys.stderr.flush()
                    
                    drum_track, sample_rate = drum_extraction(
                        audio_path,
                        dir=str(self.annoteator_path / "inference" / "pretrained_models" / "demucs"),
                        kernel='demucs',
                        mode='speed'
                    )
                    
                    logger.info("✅ drum_extraction returned successfully")
                    sys.stdout.flush()
                    sys.stderr.flush()
                    
                    elapsed = time.time() - start_time
                    logger.info(f"✅ Demucs processing completed in {elapsed:.1f} seconds")
                    
                    # Save Demucs output for inspection
                    demucs_output_path = self.output_dir / f"{output_name}_demucs_drums.wav"
                    sf.write(str(demucs_output_path), drum_track, sample_rate)
                    
                    song_duration = librosa.get_duration(y=drum_track, sr=sample_rate)
                    logger.info(f"[OK] Demucs extraction complete!")
                    logger.info(f"  - Duration: {song_duration:.2f} seconds")
                    logger.info(f"  - Sample rate: {sample_rate} Hz")
                    logger.info(f"  - Saved to: {demucs_output_path}")
                    
                except Exception as e:
                    logger.error(f"Demucs extraction failed: {e}")
                    logger.warning("Falling back to loading audio directly...")
                    drum_track, sample_rate = librosa.load(audio_path, sr=44100)
                    song_duration = librosa.get_duration(y=drum_track, sr=sample_rate)
            else:
                logger.info("")
                logger.info("STEP 1/4: LOADING AUDIO (Demucs skipped)")
                logger.info("-" * 70)
                drum_track, sample_rate = librosa.load(audio_path, sr=44100)
                song_duration = librosa.get_duration(y=drum_track, sr=sample_rate)
                logger.info(f"[OK] Audio loaded: {song_duration:.2f} seconds, {sample_rate} Hz")
            
            # Step 2: Convert to frames for prediction
            logger.info("")
            logger.info("STEP 2/4: AUDIO PREPROCESSING")
            logger.info("-" * 70)
            logger.info("🎼 Converting audio to frame-based representation...")
            logger.info("🎵 Detecting tempo (BPM)...")
            sys.stdout.flush()
            sys.stderr.flush()
            
            import time
            start_time = time.time()
            df, bpm = drum_to_frame(drum_track, sample_rate)
            elapsed = time.time() - start_time
            
            logger.info(f"✅ Preprocessing complete in {elapsed:.1f} seconds!")
            logger.info(f"  - Detected BPM: {bpm:.2f}")
            logger.info(f"  - Total frames: {len(df):,}")
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Step 3: Predict drum hits
            logger.info("")
            logger.info("STEP 3/4: NEURAL NETWORK PREDICTION")
            logger.info("-" * 70)
            logger.info(f"🧠 Loading AnNOTEator model: {self.model_path.name}")
            logger.info("🥁 Predicting drum hits for each instrument...")
            logger.info("   (Kick, Snare, Hi-Hat, Toms, Ride, Crash)")
            logger.info("Expected time: 10-30 seconds")
            sys.stdout.flush()
            sys.stderr.flush()
            
            start_time = time.time()
            prediction_df = predict_drumhit(str(self.model_path), df, sample_rate)
            elapsed = time.time() - start_time
            
            logger.info(f"✅ Predictions complete in {elapsed:.1f} seconds!")
            logger.info(f"  - Prediction frames: {len(prediction_df):,}")
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Step 4: Generate sheet music
            logger.info("")
            logger.info("STEP 4/4: MUSIC NOTATION GENERATION")
            logger.info("-" * 70)
            logger.info("📝 Constructing drum sheet music...")
            logger.info("🎶 Quantizing rhythms and organizing measures...")
            sys.stdout.flush()
            sys.stderr.flush()
            
            start_time = time.time()
            sheet_music = drum_transcriber(
                prediction_df, 
                song_duration, 
                bpm, 
                sample_rate, 
                song_title=song_title
            )
            elapsed = time.time() - start_time
            
            logger.info(f"✅ Sheet music constructed in {elapsed:.1f} seconds!")
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Step 5: Save to MusicXML
            logger.info(f"Saving to MusicXML format: {output_musicxml}")
            sheet_music.sheet.write(fp=str(output_musicxml))
            logger.info("✅ MusicXML file saved")
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Step 6: Fix percussion setup
            logger.info("Applying percussion clef fix for MuseScore...")
            self._fix_percussion_setup(str(output_musicxml))
            logger.info("✅ Percussion setup fixed")
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Extract metadata
            metadata = self._extract_metadata(prediction_df, bpm, song_duration)
            if demucs_output_path:
                metadata["demucs_output"] = str(demucs_output_path)
            
            logger.info("")
            logger.info("=" * 70)
            logger.info("[SUCCESS] TRANSCRIPTION COMPLETE!")
            logger.info("=" * 70)
            logger.info(f"Output MusicXML: {output_musicxml}")
            if demucs_output_path:
                logger.info(f"Demucs drums WAV: {demucs_output_path}")
            logger.info(f"Total notes detected: {metadata.get('total_notes', 0):,}")
            logger.info(f"BPM: {metadata.get('bpm', 0):.2f}")
            logger.info(f"Duration: {metadata.get('duration_seconds', 0):.2f} seconds")
            logger.info("=" * 70)
            
            return str(output_musicxml), metadata
            
        except Exception as e:
            logger.error(f"Error during transcription: {e}", exc_info=True)
            raise
    
    def _fix_percussion_setup(self, musicxml_path: str):
        """Fix MusicXML to display as drums in MuseScore"""
        from music21 import converter, clef, instrument, stream
        
        try:
            logger.info("Applying percussion fix...")
            
            # Load the score
            score = converter.parse(musicxml_path)
            
            # Get the part
            part = score.parts[0]
            
            # Remove existing clefs at offset 0
            clefs_to_remove = [
                elem for elem in part.flatten()
                if isinstance(elem, clef.Clef) and elem.offset == 0
            ]
            for c in clefs_to_remove:
                part.remove(c, recurse=True)
            
            # Add percussion clef at the beginning
            part.insert(0, clef.PercussionClef())
            
            # Remove existing instruments
            instruments_to_remove = [
                elem for elem in part.flatten()
                if isinstance(elem, instrument.Instrument)
            ]
            for i in instruments_to_remove:
                part.remove(i, recurse=True)
            
            # Add drumset instrument
            drumset = instrument.Instrument()
            drumset.instrumentName = "Drumset"
            drumset.midiProgram = 0
            drumset.midiChannel = 9  # MIDI channel 10 (0-indexed)
            part.insert(0, drumset)
            
            # Set part ID
            part.id = "Percussion"
            
            # Update metadata
            if not score.metadata:
                score.metadata = stream.Metadata()
            score.metadata.composer = "Generated by GrooveSheet"
            
            # Save back
            score.write('musicxml', fp=musicxml_path)
            
            logger.info("Percussion fix applied successfully")
            
        except Exception as e:
            logger.warning(f"Could not fix percussion setup: {e}")
    
    def _extract_metadata(self, prediction_df, bpm: float, duration: float) -> Dict:
        """Extract metadata from prediction results"""
        instrument_cols = ['KD', 'SD', 'HH', 'TT', 'RC', 'CC']
        instrument_names = {
            'KD': 'Kick Drum',
            'SD': 'Snare Drum',
            'HH': 'Hi-Hat',
            'TT': 'Toms',
            'RC': 'Ride Cymbal',
            'CC': 'Crash Cymbal'
        }
        
        counts = {}
        total_notes = 0
        
        for col in instrument_cols:
            if col in prediction_df.columns:
                count = int(prediction_df[col].sum())
                if count > 0:
                    counts[instrument_names.get(col, col)] = count
                    total_notes += count
        
        return {
            "total_notes": total_notes,
            "instruments_detected": counts,
            "bpm": round(bpm, 2),
            "duration_seconds": round(duration, 2),
            "model": "AnNOTEator complete_network.h5"
        }
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up temporary files older than max_age_hours"""
        import time
        current_time = time.time()
        
        cleaned_count = 0
        for file in self.output_dir.glob("transcription_*.musicxml"):
            file_age_hours = (current_time - file.stat().st_mtime) / 3600
            if file_age_hours > max_age_hours:
                file.unlink()
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old files")
        
        return cleaned_count
