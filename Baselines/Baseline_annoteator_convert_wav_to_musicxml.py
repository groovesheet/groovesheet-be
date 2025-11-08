"""
AnNOTEator Baseline WAV to MusicXML Converter
Tests all 6 pretrained models on the baseline Nirvana drums WAV file
Outputs separate MusicXML files for comparison
"""

import sys
import os
import warnings
warnings.filterwarnings('ignore')

# Set environment variables
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

print("=" * 70)
print("  AnNOTEator Baseline WAV to MusicXML Converter")
print("=" * 70)

# Add AnNOTEator to path
sys.path.insert(0, 'AnNOTEator')

try:
    from inference.input_transform import drum_to_frame
    from inference.transcriber import drum_transcriber
    from inference.prediction import predict_drumhit
    import librosa
    from music21 import converter, clef, instrument
    
    print("✓ AnNOTEator modules loaded successfully\n")
except Exception as e:
    print(f"✗ Error loading AnNOTEator modules: {e}")
    print("\nMake sure AnNOTEator folder exists in the current directory")
    sys.exit(1)

def fix_percussion_setup(musicxml_path):
    """
    Fix MusicXML to display as drums in MuseScore.
    Uses the same setup as Baseline_drum_notation.py.
    """
    print(f"   ⏳ Fixing percussion setup...")
    
    # Load the MusicXML
    score = converter.parse(musicxml_path)
    
    # Fix all parts
    for part in score.parts:
        # Remove any existing clef at offset 0 and add percussion clef
        clefs_to_remove = []
        for elem in part.flatten():
            if isinstance(elem, clef.Clef) and elem.offset == 0:
                clefs_to_remove.append(elem)
        
        for c in clefs_to_remove:
            part.remove(c, recurse=True)
        
        # Insert percussion clef at the beginning
        part.insert(0, clef.PercussionClef())
        
        # Set up the drum instrument (same as Baseline_drum_notation.py)
        drums = instrument.Instrument()
        drums.instrumentName = "Drumset"
        drums.midiProgram = 0  # Program 0
        drums.midiChannel = 9  # Channel 10 (0-indexed, so channel 9 = MIDI channel 10)
        
        # Remove any existing instruments and add our drum instrument
        instruments_to_remove = []
        for elem in part.flatten():
            if isinstance(elem, instrument.Instrument) and elem.offset == 0:
                instruments_to_remove.append(elem)
        
        for instr in instruments_to_remove:
            part.remove(instr, recurse=True)
        
        part.insert(0, drums)
        
        # Update part ID
        part.id = "Percussion"
    
    # Write the fixed MusicXML
    score.write('musicxml', fp=musicxml_path)
    print(f"   ✓ Fixed: Added PercussionClef and Drumset (MIDI channel 10)")

# Configuration
WAV_PATH = r"d:\Coding Files\GitHub\drumscore-be\Baseline_nirvana_drums.wav"
OUTPUT_DIR = r"d:\Coding Files\GitHub\drumscore-be\test_output\annoteator_models"

# All available pretrained models
# Note: Only complete_network exists in the current repo
PRETRAINED_MODELS = {
    'complete_network': 'AnNOTEator/inference/pretrained_models/annoteators/complete_network.h5',
    # Uncomment if these models exist in your repo:
    # 'crash_network': 'AnNOTEator/inference/pretrained_models/annoteators/crash_network.h5',
    # 'hihat_network': 'AnNOTEator/inference/pretrained_models/annoteators/hihat_network.h5',
    # 'kick_network': 'AnNOTEator/inference/pretrained_models/annoteators/kick_network.h5',
    # 'ride_network': 'AnNOTEator/inference/pretrained_models/annoteators/ride_network.h5',
    # 'snare_network': 'AnNOTEator/inference/pretrained_models/annoteators/snare_network.h5',
}

# Check if WAV file exists
if not os.path.exists(WAV_PATH):
    print(f"✗ Error: WAV file not found at: {WAV_PATH}")
    print("\nUsage: Make sure Baseline_nirvana_drums.wav exists")
    sys.exit(1)

print(f"✓ Found audio file: {WAV_PATH}")
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"✓ Output directory: {OUTPUT_DIR}\n")

# Load audio once (shared across all models)
print("=" * 70)
print("[STEP 1] Loading Audio File")
print("=" * 70)

try:
    print("⏳ Loading drum track (mono)...")
    drum_track, sr = librosa.load(WAV_PATH, sr=None, mono=True)
    
    print(f"✓ Audio loaded successfully")
    print(f"   Sample rate: {sr} Hz")
    print(f"   Duration: {librosa.get_duration(y=drum_track, sr=sr):.2f} seconds")
    print(f"   Audio shape: {drum_track.shape}")
    
    song_duration = librosa.get_duration(y=drum_track, sr=sr)
    
except Exception as e:
    print(f"✗ Error loading audio: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Convert to frames once (shared across all models)
print("\n" + "=" * 70)
print("[STEP 2] Converting to Frames")
print("=" * 70)

try:
    print("⏳ Converting drum track to frames...")
    df, bpm = drum_to_frame(drum_track, sr, estimated_bpm=None, resolution=16)
    
    print(f"✓ Frame conversion complete")
    print(f"   Detected BPM: {bpm}")
    print(f"   Frame data shape: {df.shape}")
    
except Exception as e:
    print(f"✗ Error converting to frames: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test each model
print("\n" + "=" * 70)
print("[STEP 3] Testing All Pretrained Models")
print("=" * 70)

results = {}

for model_name, model_path in PRETRAINED_MODELS.items():
    print(f"\n{'─' * 70}")
    print(f"🔧 Model: {model_name}")
    print(f"{'─' * 70}")
    
    if not os.path.exists(model_path):
        print(f"⚠️  Warning: Model file not found: {model_path}")
        print(f"   Skipping {model_name}...")
        results[model_name] = {'status': 'missing', 'error': 'Model file not found'}
        continue
    
    try:
        # Predict drum hits
        print(f"⏳ Predicting drum hits with {model_name}...")
        df_pred = predict_drumhit(model_path, df, sr)
        
        print(f"✓ Prediction complete")
        print(f"   Predicted {len(df_pred)} drum hits")
        
        # Check dataframe structure
        print(f"   DataFrame columns: {list(df_pred.columns)}")
        print(f"   DataFrame shape: {df_pred.shape}")
        
        # Count hits by instrument (if column exists)
        hit_counts = {}
        if 'instrument' in df_pred.columns:
            for _, row in df_pred.iterrows():
                instrument = row['instrument']
                if instrument not in hit_counts:
                    hit_counts[instrument] = 0
                hit_counts[instrument] += 1
            
            print(f"\n   📊 Drum hits by instrument:")
            for instrument, count in sorted(hit_counts.items()):
                print(f"      • {instrument:15s}: {count:4d} hits")
        else:
            print(f"\n   📊 DataFrame preview:")
            print(df_pred.head())
        
        # Create sheet music
        print(f"\n⏳ Creating sheet music...")
        sheet_music = drum_transcriber(
            df_pred,
            song_duration,
            bpm,
            sr,
            beats_in_measure=4,
            note_value=4,
            song_title=f'Nirvana Drums - {model_name}'
        )
        
        # Save MusicXML
        output_file = os.path.join(OUTPUT_DIR, f"nirvana_{model_name}.musicxml")
        sheet_music.sheet.write(fp=output_file)
        
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✓ MusicXML saved: {output_file}")
            print(f"   File size: {file_size:,} bytes")
            
            # Fix the percussion setup so it displays as drums in MuseScore
            fix_percussion_setup(output_file)
            
            # Get updated file size after fix
            file_size = os.path.getsize(output_file)
            
            results[model_name] = {
                'status': 'success',
                'hits': len(df_pred),
                'hit_counts': hit_counts,
                'file': output_file,
                'file_size': file_size
            }
        else:
            print(f"✗ Error: MusicXML file was not created")
            results[model_name] = {'status': 'failed', 'error': 'File not created'}
        
    except Exception as e:
        print(f"✗ Error processing with {model_name}: {e}")
        import traceback
        traceback.print_exc()
        results[model_name] = {'status': 'error', 'error': str(e)}

# Summary
print("\n" + "=" * 70)
print("📊 SUMMARY - All Models Tested")
print("=" * 70)

print(f"\n📁 Output directory: {OUTPUT_DIR}")
print(f"\n✅ Successfully processed models:")

success_count = 0
for model_name, result in results.items():
    if result['status'] == 'success':
        success_count += 1
        print(f"\n   🎵 {model_name}:")
        print(f"      • File: nirvana_{model_name}.musicxml")
        print(f"      • Size: {result['file_size']:,} bytes")
        print(f"      • Total hits: {result['hits']}")
        print(f"      • Instruments detected:")
        for instrument, count in sorted(result['hit_counts'].items()):
            print(f"         - {instrument:15s}: {count:4d} hits")

if success_count == 0:
    print("   (None)")

failed_count = len([r for r in results.values() if r['status'] != 'success'])
if failed_count > 0:
    print(f"\n⚠️  Failed/Missing models: {failed_count}")
    for model_name, result in results.items():
        if result['status'] != 'success':
            print(f"   • {model_name}: {result.get('error', 'Unknown error')}")

print("\n" + "=" * 70)
print("💡 NEXT STEPS:")
print("=" * 70)
print("1. Open each MusicXML file in MuseScore")
print("2. Compare the transcription quality:")
print("   • Accuracy of drum hits")
print("   • Timing precision")
print("   • Instrument detection (kick, snare, hi-hat, etc.)")
print("3. Identify which model produces the best results")
print("\n📌 Model descriptions:")
print("   • complete_network: All drum instruments (recommended)")
print("   • kick_network: Specialized for kick/bass drum")
print("   • snare_network: Specialized for snare drum")
print("   • hihat_network: Specialized for hi-hat")
print("   • ride_network: Specialized for ride cymbal")
print("   • crash_network: Specialized for crash cymbal")
print("=" * 70)

print(f"\n✓ Done! Processed {success_count}/{len(PRETRAINED_MODELS)} models successfully")
