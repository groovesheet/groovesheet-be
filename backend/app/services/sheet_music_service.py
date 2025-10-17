"""
Sheet music generation service
Converts MIDI to MusicXML notation
"""
import os
import logging
from typing import Optional
from music21 import converter, stream, layout, instrument, clef, meter, tempo
from music21 import note, duration, pitch

from app.core.config import settings

logger = logging.getLogger(__name__)


class SheetMusicService:
    """Service for converting MIDI to MusicXML notation"""
    
    # Drum MIDI note mapping (General MIDI percussion)
    DRUM_MAP = {
        36: 'Bass Drum',      # Kick
        38: 'Snare',          # Snare
        40: 'Snare Rim',      # Snare rim
        42: 'Hi-Hat Closed',  # Closed Hi-hat
        44: 'Hi-Hat Pedal',   # Pedal Hi-hat
        46: 'Hi-Hat Open',    # Open Hi-hat
        48: 'Tom High',       # High tom
        49: 'Crash',          # Crash cymbal
        50: 'Tom High',       # High tom
        51: 'Ride',           # Ride cymbal
        45: 'Tom Low',        # Low tom
        47: 'Tom Mid',        # Mid tom
        41: 'Tom Low',        # Low floor tom
        43: 'Tom Low',        # High floor tom
        55: 'Splash',         # Splash cymbal
        57: 'Crash',          # Crash cymbal 2
    }
    
    def __init__(self):
        logger.info("SheetMusicService initialized")
        self._configure_music21()
    
    def _configure_music21(self):
        """Configure music21 settings"""
        try:
            # Set MuseScore path if available (for better rendering)
            # This should be configured in environment variables
            musescore_path = os.environ.get('MUSESCORE_PATH')
            if musescore_path and os.path.exists(musescore_path):
                from music21 import environment
                env = environment.Environment()
                env['musescoreDirectPNGPath'] = musescore_path
                logger.info(f"MuseScore configured at: {musescore_path}")
        except Exception as e:
            logger.warning(f"Could not configure MuseScore: {str(e)}")
    
    async def midi_to_musicxml(
        self,
        midi_path: str,
        output_dir: str,
        filename: Optional[str] = None
    ) -> str:
        """
        Convert MIDI file to MusicXML notation
        
        Args:
            midi_path: Path to input MIDI file
            output_dir: Directory to save MusicXML
            filename: Optional output filename (without extension)
            
        Returns:
            Path to generated MusicXML file
        """
        try:
            logger.info(f"Converting MIDI to MusicXML: {midi_path}")
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Load MIDI file
            midi_stream = converter.parse(midi_path)
            
            # Process and enhance for drum notation
            processed_stream = self._process_drum_notation(midi_stream)
            
            # Determine output path
            if filename is None:
                filename = os.path.splitext(os.path.basename(midi_path))[0]
            
            musicxml_path = os.path.join(output_dir, f"{filename}.musicxml")
            
            # Generate MusicXML using music21
            processed_stream.write('musicxml', fp=musicxml_path)
            logger.info(f"MusicXML generated: {musicxml_path}")
            
            # Verify file was created
            if not os.path.exists(musicxml_path):
                raise FileNotFoundError(f"MusicXML file was not created at {musicxml_path}")
            
            file_size = os.path.getsize(musicxml_path)
            logger.info(f"MusicXML file size: {file_size} bytes")
            
            return musicxml_path
            
        except Exception as e:
            logger.error(f"Error converting MIDI to MusicXML: {str(e)}")
            raise
    
    # Keep the old method for backward compatibility, but have it call the new one
    async def midi_to_pdf(
        self,
        midi_path: str,
        output_dir: str,
        filename: Optional[str] = None
    ) -> str:
        """
        Legacy method - now generates MusicXML instead of PDF
        
        Args:
            midi_path: Path to input MIDI file
            output_dir: Directory to save MusicXML
            filename: Optional output filename (without extension)
            
        Returns:
            Path to generated MusicXML file
        """
        logger.warning("midi_to_pdf is deprecated, generating MusicXML instead")
        return await self.midi_to_musicxml(midi_path, output_dir, filename)
    
    def _process_drum_notation(self, midi_stream: stream.Stream) -> stream.Score:
        """
        Process MIDI stream for drum notation
        
        Args:
            midi_stream: Input MIDI stream
            
        Returns:
            Processed music21 Score with drum notation
        """
        try:
            # Create a new score
            score = stream.Score()
            
            # Add metadata
            score.metadata = midi_stream.metadata if midi_stream.metadata else stream.Metadata()
            score.metadata.title = "Drum Transcription"
            score.metadata.composer = "Generated by DrumScore"
            
            # Create drum part
            drum_part = stream.Part()
            drum_part.partName = "Drums"
            
            # Set up drum staff (percussion clef)
            drum_staff = clef.PercussionClef()
            drum_part.append(drum_staff)
            
            # Add time signature (detect from MIDI or default to 4/4)
            time_sig = midi_stream.recurse().getElementsByClass(meter.TimeSignature).first()
            if time_sig:
                drum_part.append(time_sig)
            else:
                drum_part.append(meter.TimeSignature('4/4'))
            
            # Add tempo marking
            tempo_mark = tempo.MetronomeMark(number=120)
            drum_part.append(tempo_mark)
            
            # Extract and process notes
            notes_and_rests = []
            for element in midi_stream.flatten().notesAndRests:
                if isinstance(element, note.Note):
                    # Map MIDI pitch to drum notation
                    drum_note = self._create_drum_note(element)
                    if drum_note:
                        notes_and_rests.append(drum_note)
                elif isinstance(element, note.Rest):
                    notes_and_rests.append(element)
            
            # Add notes to part
            for item in notes_and_rests:
                drum_part.append(item)
            
            # Add part to score
            score.append(drum_part)
            
            # Add page layout
            score.insert(0, layout.PageLayout(
                pageHeight=11 * 72,  # 11 inches in points
                pageWidth=8.5 * 72,  # 8.5 inches in points
                leftMargin=0.5 * 72,
                rightMargin=0.5 * 72,
                topMargin=0.5 * 72,
                bottomMargin=0.5 * 72
            ))
            
            return score
            
        except Exception as e:
            logger.error(f"Error processing drum notation: {str(e)}")
            # Return original stream if processing fails
            return midi_stream
    
    def _create_drum_note(self, midi_note: note.Note) -> Optional[note.Note]:
        """
        Create a drum notation note from MIDI note
        
        Args:
            midi_note: Input MIDI note
            
        Returns:
            Drum notation note or None
        """
        try:
            # Get MIDI pitch number
            midi_num = midi_note.pitch.midi
            
            # Map to drum instrument
            if midi_num in self.DRUM_MAP:
                drum_note = note.Note()
                drum_note.duration = midi_note.duration
                drum_note.offset = midi_note.offset
                
                # Set pitch for drum notation (using standard drum staff positions)
                # Standard drum staff: Line 1 (bottom) = Bass drum, Line 3 = Snare, etc.
                if midi_num in [36]:  # Bass drum
                    drum_note.pitch = pitch.Pitch('F4')
                    drum_note.notehead = 'x'
                elif midi_num in [38, 40]:  # Snare
                    drum_note.pitch = pitch.Pitch('C5')
                elif midi_num in [42, 44]:  # Closed hi-hat
                    drum_note.pitch = pitch.Pitch('G5')
                    drum_note.notehead = 'x'
                elif midi_num in [46]:  # Open hi-hat
                    drum_note.pitch = pitch.Pitch('A5')
                    drum_note.notehead = 'circle-x'
                elif midi_num in [49, 57]:  # Crash
                    drum_note.pitch = pitch.Pitch('A5')
                    drum_note.notehead = 'x'
                elif midi_num in [51]:  # Ride
                    drum_note.pitch = pitch.Pitch('F5')
                    drum_note.notehead = 'x'
                else:  # Toms
                    drum_note.pitch = pitch.Pitch('E5')
                
                # Preserve velocity (dynamics)
                if hasattr(midi_note, 'volume'):
                    drum_note.volume = midi_note.volume
                
                return drum_note
            
            return None
            
        except Exception as e:
            logger.warning(f"Error creating drum note: {str(e)}")
            return None
    

