"""
Simple direct test - just test the API (start server manually first)
"""
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
AUDIO_FILE = r"D:\Coding Files\GitHub\drumscore-be\Nirvana - Smells Like Teen Spirit - drums only. Isolated drum track..mp3"
SONG_TITLE = "Nirvana - Smells Like Teen Spirit (Drums)"

print("\n" + "🎵" * 70)
print("  AnNOTEator API Test (Server must be running)")
print("🎵" * 70)
print("\n💡 Make sure the server is running:")
print("   cd backend")
print("   python -m uvicorn main:app --host 127.0.0.1 --port 8000")
print()

input("Press Enter when server is ready...")

# Test health
print("\n[1/3] Health Check...")
try:
    response = requests.get(f"{BASE_URL}/api/annoteator/health", timeout=5)
    if response.status_code == 200:
        health = response.json()
        print(f"   ✓ Status: {health['status']}")
        print(f"   ✓ Model exists: {health['model_exists']}")
    else:
        print(f"   ✗ Health check failed: {response.status_code}")
        exit(1)
except Exception as e:
    print(f"   ✗ Cannot connect to server: {e}")
    print("\n   Please start the server first!")
    exit(1)

# Upload and transcribe
print(f"\n[2/3] Uploading & Transcribing...")
print(f"   File: {Path(AUDIO_FILE).name}")
print(f"   Size: {Path(AUDIO_FILE).stat().st_size / (1024*1024):.2f} MB")
print(f"\n   📋 Pipeline steps:")
print(f"   1️⃣  Demucs drum extraction")
print(f"   2️⃣  Audio preprocessing & BPM detection")
print(f"   3️⃣  Neural network prediction")
print(f"   4️⃣  MusicXML generation")
print(f"\n   ⏳ Processing (watch server terminal for detailed logs)...\n")

try:
    with open(AUDIO_FILE, "rb") as f:
        files = {"file": (Path(AUDIO_FILE).name, f, "audio/mpeg")}
        data = {"song_title": SONG_TITLE}
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/annoteator/upload",
            files=files,
            data=data,
            timeout=300  # 5 minutes
        )
        elapsed = time.time() - start_time
    
    print(f"   ⏱️  Total time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n   ✅ SUCCESS!\n")
        
        metadata = result.get("metadata", {})
        print(f"   📊 Results:")
        print(f"   • Session ID: {result.get('session_id')}")
        print(f"   • Total notes: {metadata.get('total_notes', 0):,}")
        print(f"   • BPM: {metadata.get('bpm', 0):.2f}")
        print(f"   • Duration: {metadata.get('duration_seconds', 0):.2f} seconds")
        print(f"   • Model: {metadata.get('model', 'N/A')}")
        
        instruments = metadata.get('instruments_detected', {})
        if instruments:
            print(f"\n   🥁 Instruments detected:")
            for inst, count in instruments.items():
                print(f"      • {inst}: {count:,} hits")
        
        # Show file paths
        print(f"\n   📁 Files generated:")
        
        # Check Demucs output
        demucs_path = metadata.get('demucs_output')
        if demucs_path:
            # The path is relative to backend/ directory
            if not Path(demucs_path).is_absolute():
                demucs_full_path = Path("backend") / demucs_path
            else:
                demucs_full_path = Path(demucs_path)
            
            demucs_exists = demucs_full_path.exists()
            print(f"      • Demucs drums WAV:")
            print(f"        Relative path: {demucs_path}")
            print(f"        Full path: {demucs_full_path.absolute()}")
            print(f"        Exists: {'✓ YES' if demucs_exists else '✗ NO - FILE NOT FOUND!'}")
            if demucs_exists:
                size_mb = demucs_full_path.stat().st_size / (1024*1024)
                print(f"        Size: {size_mb:.2f} MB")
        else:
            print(f"      • Demucs drums WAV: ✗ Not generated (check logs)")
        
        # Check MusicXML
        musicxml_path = result.get('musicxml_path')
        if musicxml_path:
            # The path is relative to backend/ directory
            if not Path(musicxml_path).is_absolute():
                musicxml_full_path = Path("backend") / musicxml_path
            else:
                musicxml_full_path = Path(musicxml_path)
            
            musicxml_exists = musicxml_full_path.exists()
            print(f"      • MusicXML:")
            print(f"        Relative path: {musicxml_path}")
            print(f"        Full path: {musicxml_full_path.absolute()}")
            print(f"        Exists: {'✓ YES' if musicxml_exists else '✗ NO - FILE NOT FOUND!'}")
            if musicxml_exists:
                size_kb = musicxml_full_path.stat().st_size / 1024
                print(f"        Size: {size_kb:.2f} KB")
        else:
            print(f"      • MusicXML: ✗ Not generated (check logs)")
        
        # Download
        print(f"\n[3/3] Downloading MusicXML...")
        session_id = result.get("session_id")
        if session_id:
            download_response = requests.get(f"{BASE_URL}/api/annoteator/download/{session_id}")
            
            if download_response.status_code == 200:
                output_file = f"nirvana_transcription_{session_id}.musicxml"
                with open(output_file, "wb") as f:
                    f.write(download_response.content)
                
                print(f"   ✓ Downloaded: {output_file}")
                print(f"   ✓ Size: {len(download_response.content) / 1024:.2f} KB")
                
                print(f"\n{'='*70}")
                print(f"🎉 TEST COMPLETE!")
                print(f"{'='*70}")
                print(f"\n💡 Next steps:")
                print(f"   1. Open '{output_file}' in MuseScore")
                print(f"   2. Check the drum notation")
                print(f"   3. Compare with original audio")
                
                if demucs_path:
                    print(f"\n✓ Full file paths:")
                    # Construct absolute paths
                    if not Path(demucs_path).is_absolute():
                        demucs_abs = (Path("backend") / demucs_path).absolute()
                    else:
                        demucs_abs = Path(demucs_path)
                    
                    if musicxml_path and not Path(musicxml_path).is_absolute():
                        musicxml_abs = (Path("backend") / musicxml_path).absolute()
                    else:
                        musicxml_abs = Path(musicxml_path) if musicxml_path else None
                    
                    print(f"   • Demucs WAV: {demucs_abs}")
                    if musicxml_abs:
                        print(f"   • MusicXML: {musicxml_abs}")
                    print(f"   • Downloaded: {Path(output_file).absolute()}")
            else:
                print(f"   ✗ Download failed: {download_response.status_code}")
    else:
        print(f"\n   ✗ FAILED!")
        print(f"   Status: {response.status_code}")
        print(f"   Error: {response.text}")

except requests.exceptions.Timeout:
    print(f"\n   ✗ Request timed out (>5 minutes)")
except Exception as e:
    print(f"\n   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print()
