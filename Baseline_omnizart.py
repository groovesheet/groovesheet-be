"""
Baseline Omnizart Transcription Script
Uses Omnizart's default transcribe() method to generate MIDI and MusicXML
This is the baseline/standard way to use Omnizart (3 drum classes: kick, snare, hi-hat)
"""

import sys
import os
import warnings
warnings.filterwarnings('ignore')

# Set environment variables
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

print("=" * 70)
print("  Baseline Omnizart Drum Transcription")
print("=" * 70)

# ==================== Multiprocessing Patch ====================
from concurrent.futures import Future

class FakeProcessPoolExecutor:
    def __init__(self, max_workers=None):
        self.max_workers = max_workers
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def submit(self, fn, *args, **kwargs):
        future = Future()
        try:
            result = fn(*args, **kwargs)
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)
        return future

import concurrent.futures
concurrent.futures.ProcessPoolExecutor = FakeProcessPoolExecutor

import multiprocessing
import multiprocessing.pool

class FakePool:
    def __init__(self, processes=None, initializer=None, initargs=(), maxtasksperchild=None, context=None):
        self.processes = processes
        if initializer:
            initializer(*initargs)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def map(self, func, iterable, chunksize=None):
        return [func(x) for x in iterable]
    def starmap(self, func, iterable, chunksize=None):
        return [func(*args) for args in iterable]
    def apply_async(self, func, args=(), kwds=None, callback=None, error_callback=None):
        if kwds is None:
            kwds = {}
        try:
            result = func(*args, **kwds)
            if callback:
                callback(result)
            return FakeAsyncResult(result, None)
        except Exception as e:
            if error_callback:
                error_callback(e)
            return FakeAsyncResult(None, e)
    def close(self):
        pass
    def join(self):
        pass
    def terminate(self):
        pass

class FakeAsyncResult:
    def __init__(self, result, exception):
        self._result = result
        self._exception = exception
    def get(self, timeout=None):
        if self._exception:
            raise self._exception
        return self._result
    def ready(self):
        return True
    def successful(self):
        return self._exception is None

multiprocessing.Pool = FakePool
multiprocessing.pool.Pool = FakePool

print("✓ Multiprocessing disabled\n")

# ====================
# Configuration
# ====================

# Default audio path (can be overridden by command line argument)
DRUM_WAV_PATH = r"d:\Coding Files\GitHub\drumscore-be\Baseline_nirvana_drums.wav"
OUTPUT_DIR = r"d:\Coding Files\GitHub\drumscore-be\test_output"

# Check if user provided a file as command line argument
if len(sys.argv) > 1:
    DRUM_WAV_PATH = sys.argv[1]
    print(f"Using provided audio file: {DRUM_WAV_PATH}")

if not os.path.exists(DRUM_WAV_PATH):
    print(f"✗ Error: Drum file not found at: {DRUM_WAV_PATH}")
    print(f"\nUsage: python baseline_omnizart.py [path_to_drum_audio.wav]")
    sys.exit(1)

print(f"✓ Found drum audio: {DRUM_WAV_PATH}")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ====================
# Transcribe with Omnizart (Default Method)
# ====================
print("\n🥁 Starting Omnizart drum transcription (baseline method)...")
print("   Using Omnizart's default transcribe() function")
print("   Output: 3 drum classes (kick, snare, hi-hat)\n")

try:
    from omnizart.drum import app as drum_app
    
    print("⏳ Transcribing with Omnizart...")
    
    # Output MIDI path
    omnizart_midi = os.path.join(OUTPUT_DIR, "baseline_omnizart.mid")
    
    # Transcribe using Omnizart's default method
    drum_app.transcribe(DRUM_WAV_PATH, output=omnizart_midi)
    
    print(f"✓ Omnizart MIDI generated: {omnizart_midi}")
    
    if os.path.exists(omnizart_midi):
        midi_size = os.path.getsize(omnizart_midi)
        print(f"   File size: {midi_size:,} bytes")
    
    # ====================
    # Convert MIDI to MusicXML
    # ====================
    print("\n⏳ Converting to MusicXML...")
    
    from music21 import converter, stream, tempo, meter, instrument, clef
    
    # Load MIDI
    score = converter.parse(omnizart_midi)
    
    # Set up drum notation
    drum_part = stream.Part()
    drum_part.append(clef.PercussionClef())
    
    # Set the instrument to drums (MIDI program 0, channel 10 for drums)
    drums = instrument.Instrument()
    drums.instrumentName = "Drumset"
    drums.midiProgram = 0  # Program 0
    drums.midiChannel = 9  # Channel 10 (0-indexed, so channel 9 = MIDI channel 10)
    drum_part.insert(0, drums)
    
    drum_part.append(meter.TimeSignature('4/4'))
    drum_part.append(tempo.MetronomeMark(number=120))
    
    # Copy notes from MIDI
    for element in score.flatten().notesAndRests:
        drum_part.append(element)
    
    # Create score
    drum_score = stream.Score()
    drum_score.append(drum_part)
    
    # Save MusicXML
    omnizart_xml = os.path.join(OUTPUT_DIR, "baseline_omnizart.musicxml")
    drum_score.write('musicxml', fp=omnizart_xml)
    
    if os.path.exists(omnizart_xml):
        xml_file_size = os.path.getsize(omnizart_xml)
        print(f"✓ MusicXML file: {omnizart_xml}")
        print(f"   File size: {xml_file_size:,} bytes")
    else:
        print(f"✗ Error: MusicXML file was not created")
    
    # ====================
    # Summary
    # ====================
    print("\n" + "=" * 70)
    print("✓ BASELINE OMNIZART TRANSCRIPTION COMPLETE")
    print("=" * 70)
    
    print(f"\n📁 Generated files in '{OUTPUT_DIR}/':")
    print(f"   🎹 MIDI: baseline_omnizart.mid ({midi_size:,} bytes)")
    print(f"   📄 MusicXML: baseline_omnizart.musicxml ({xml_file_size:,} bytes)")
    
    print("\n📊 Output Details:")
    print("   • Method: Omnizart default transcribe() function")
    print("   • Drum classes: 3 (kick, snare, hi-hat)")
    print("   • Processing: Black-box inference (Omnizart internal)")
    print("   • MIDI mapping: Omnizart default")
    
    print("\n💡 Compare with:")
    print("   • drums_6_classes.mid (6 classes with custom grouping)")
    print("   • drum_notation_demo.musicxml (manual baseline notation)")
    
except Exception as e:
    print(f"\n✗ Transcription failed: {e}")
    import traceback
    traceback.print_exc()

print("\n✓ Done")
