"""
Standalone Demucs test script
Tests drum separation with a sample audio file
"""
import os
import sys

# Add demucs to path
sys.path.insert(0, './demucs')

def test_demucs_separation(audio_file):
    """Test Demucs drum separation"""
    print("=" * 70)
    print("DEMUCS STANDALONE TEST")
    print("=" * 70)
    print(f"Input file: {audio_file}")
    print("")
    
    # Import Demucs
    print("Importing Demucs...")
    try:
        from demucs.api import Separator
        print("✓ Demucs API imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Demucs API: {e}")
        print("\nTrying alternative import...")
        from demucs.apply import apply_model
        from demucs.pretrained import get_model
        print("✓ Using alternative Demucs imports")
    
    print("")
    print("Initializing Demucs separator...")
    print("Model: htdemucs (default)")
    print("Device: CPU")
    print("Progress bar: ENABLED")
    print("")
    
    try:
        # Try API approach first with progress bar enabled
        separator = Separator(model="htdemucs", device="cpu", progress=True)
        print("✓ Separator initialized")
        print("")
        
        print("Starting separation (this may take 2-3 minutes)...")
        print("-" * 70)
        
        # Separate stems
        origin, stems = separator.separate_audio_file(audio_file)
        
        print("-" * 70)
        print("✓ Separation complete!")
        print("")
        print(f"Origin shape: {origin.shape}")
        print(f"Number of stems: {len(stems)}")
        print("")
        print("Available stems:")
        for stem_name, stem_data in stems.items():
            print(f"  - {stem_name}: {stem_data.shape}")
        
        # Get drums
        drums = stems['drums']
        print("")
        print(f"✓ Drums extracted: {drums.shape}")
        print("")
        
        # Save drums to file
        output_file = "./test_output/demucs_drums_test.wav"
        os.makedirs("./test_output", exist_ok=True)
        
        import soundfile as sf
        import numpy as np
        
        # Transpose to (samples, channels) for soundfile
        drums_transposed = np.transpose(drums, (1, 0))
        sf.write(output_file, drums_transposed, 44100)
        
        print(f"✓ Drums saved to: {output_file}")
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"  File size: {file_size_mb:.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Test with Nirvana MP3
    audio_file = r"D:\Coding Files\GitHub\groovesheet\groovesheet-be\Nirvana - Smells Like Teen Spirit (Official Music Video).mp3"
    
    if not os.path.exists(audio_file):
        print(f"Error: File not found: {audio_file}")
        print("Please update the audio_file path in the script")
        sys.exit(1)
    
    success = test_demucs_separation(audio_file)
    
    if success:
        print("")
        print("=" * 70)
        print("TEST PASSED ✓")
        print("=" * 70)
    else:
        print("")
        print("=" * 70)
        print("TEST FAILED ✗")
        print("=" * 70)
        sys.exit(1)
