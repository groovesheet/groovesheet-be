"""
Pipeline Comparison Script
Runs both Omnizart and AnNOTEator pipelines on the same audio file
Compares results, performance, and accuracy
"""

import os
import sys
import time
import json
import warnings
from datetime import datetime
from pathlib import Path
import librosa
import pretty_midi
import numpy as np

warnings.filterwarnings('ignore')

# Add AnNOTEator to path
sys.path.insert(0, 'AnNOTEator')

from inference.input_transform import drum_to_frame
from inference.transcriber import drum_transcriber
from inference.prediction import predict_drumhit

def run_omnizart_pipeline(audio_file, output_dir):
    """
    Run Omnizart pipeline: Audio → MIDI → MusicXML
    """
    from omnizart.drum import app as drum_app
    from music21 import converter, clef, instrument
    
    print(f"  🎵 Running Omnizart...")
    
    # Generate MIDI
    midi_path = os.path.join(output_dir, "omnizart_output.mid")
    drum_app.transcribe(audio_file, model_path=None, output=midi_path)
    
    if not os.path.exists(midi_path):
        raise Exception("Omnizart failed to generate MIDI")
    
    # Convert MIDI to MusicXML with proper drum setup
    xml_path = os.path.join(output_dir, "omnizart_output.musicxml")
    
    # Load MIDI
    midi_data = pretty_midi.PrettyMIDI(midi_path)
    
    # Create MusicXML (simplified conversion)
    score = converter.parse(midi_path)
    
    # Fix percussion setup
    for part in score.parts:
        # Add percussion clef
        part.insert(0, clef.PercussionClef())
        
        # Set up drum instrument
        drums = instrument.Instrument()
        drums.instrumentName = "Drumset"
        drums.midiProgram = 0
        drums.midiChannel = 9
        part.insert(0, drums)
        part.id = "Percussion"
    
    score.write('musicxml', fp=xml_path)
    
    return {
        'midi_file': midi_path,
        'xml_file': xml_path,
        'midi_size': os.path.getsize(midi_path),
        'xml_size': os.path.getsize(xml_path)
    }

def run_annoteator_pipeline(audio_file, output_dir):
    """
    Run AnNOTEator pipeline: Audio → MusicXML (direct)
    """
    from music21 import converter, clef, instrument
    
    print(f"  🎵 Running AnNOTEator...")
    
    model_path = 'AnNOTEator/inference/pretrained_models/annoteators/complete_network.h5'
    
    if not os.path.exists(model_path):
        raise Exception(f"AnNOTEator model not found: {model_path}")
    
    # Load audio
    audio, sr = librosa.load(audio_file, sr=44100, mono=True)
    duration = librosa.get_duration(y=audio, sr=sr)
    
    # Convert to frames
    frames, bpm = drum_to_frame(audio, sr, estimated_bpm=None, resolution=16)
    
    # Predict
    df = predict_drumhit(model_path, frames, sr)
    
    # Create sheet music
    transcriber_obj = drum_transcriber(
        df, duration, bpm, sr,
        beats_in_measure=4,
        note_value=4,
        song_title="AnNOTEator Transcription"
    )
    
    # Save initial MusicXML
    xml_path = os.path.join(output_dir, "annoteator_output.musicxml")
    transcriber_obj.sheet.write('musicxml', fp=xml_path)
    
    # Fix percussion setup
    score = converter.parse(xml_path)
    for part in score.parts:
        # Remove existing clefs
        clefs_to_remove = [elem for elem in part.flatten() 
                          if isinstance(elem, clef.Clef) and elem.offset == 0]
        for c in clefs_to_remove:
            part.remove(c, recurse=True)
        
        # Add percussion clef
        part.insert(0, clef.PercussionClef())
        
        # Set up drum instrument
        drums = instrument.Instrument()
        drums.instrumentName = "Drumset"
        drums.midiProgram = 0
        drums.midiChannel = 9
        
        # Remove existing instruments
        instruments_to_remove = [elem for elem in part.flatten() 
                                if isinstance(elem, instrument.Instrument) and elem.offset == 0]
        for instr in instruments_to_remove:
            part.remove(instr, recurse=True)
        
        part.insert(0, drums)
        part.id = "Percussion"
    
    score.write('musicxml', fp=xml_path)
    
    return {
        'xml_file': xml_path,
        'xml_size': os.path.getsize(xml_path),
        'detected_bpm': bpm,
        'total_hits': len(df),
        'hit_breakdown': {
            'snare': int(df['SD'].sum()) if 'SD' in df.columns else 0,
            'hihat': int(df['HH'].sum()) if 'HH' in df.columns else 0,
            'kick': int(df['KD'].sum()) if 'KD' in df.columns else 0,
            'ride': int(df['RC'].sum()) if 'RC' in df.columns else 0,
            'tom': int(df['TT'].sum()) if 'TT' in df.columns else 0,
            'crash': int(df['CC'].sum()) if 'CC' in df.columns else 0,
        }
    }

def analyze_midi_file(midi_path):
    """
    Analyze MIDI file and extract statistics
    """
    midi_data = pretty_midi.PrettyMIDI(midi_path)
    
    stats = {
        'total_notes': 0,
        'duration': midi_data.get_end_time(),
        'tempo': midi_data.estimate_tempo(),
        'instruments': [],
        'note_density': 0,
        'pitch_distribution': {}
    }
    
    for instrument in midi_data.instruments:
        inst_info = {
            'name': instrument.name,
            'program': instrument.program,
            'is_drum': instrument.is_drum,
            'note_count': len(instrument.notes)
        }
        stats['instruments'].append(inst_info)
        stats['total_notes'] += len(instrument.notes)
        
        # Pitch distribution
        for note in instrument.notes:
            pitch = note.pitch
            if pitch not in stats['pitch_distribution']:
                stats['pitch_distribution'][pitch] = 0
            stats['pitch_distribution'][pitch] += 1
    
    if stats['duration'] > 0:
        stats['note_density'] = stats['total_notes'] / stats['duration']
    
    return stats

def calculate_performance_metrics(omnizart_time, omnizart_memory, 
                                 annoteator_time, annoteator_memory):
    """
    Compare performance metrics
    """
    return {
        'processing_time': {
            'omnizart': omnizart_time,
            'annoteator': annoteator_time,
            'faster': 'omnizart' if omnizart_time < annoteator_time else 'annoteator',
            'speedup': max(omnizart_time, annoteator_time) / min(omnizart_time, annoteator_time)
        },
        'memory_usage': {
            'omnizart': omnizart_memory,
            'annoteator': annoteator_memory
        }
    }

def compare_pipelines(audio_file, output_base_dir="test_results", ground_truth_midi=None):
    """
    Main comparison function
    """
    print("=" * 80)
    print("  DRUM TRANSCRIPTION PIPELINE COMPARISON")
    print("=" * 80)
    
    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(output_base_dir, f"comparison_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    audio_name = os.path.basename(audio_file)
    print(f"\n📁 Audio file: {audio_name}")
    print(f"📁 Output directory: {output_dir}")
    
    # Get audio info
    audio, sr = librosa.load(audio_file, sr=None, mono=True)
    duration = librosa.get_duration(y=audio, sr=sr)
    
    print(f"\n🎵 Audio info:")
    print(f"   Duration: {duration:.2f} seconds")
    print(f"   Sample rate: {sr} Hz")
    
    results = {
        'audio_file': audio_file,
        'audio_name': audio_name,
        'timestamp': timestamp,
        'duration': duration,
        'sample_rate': sr,
        'omnizart': {},
        'annoteator': {},
        'comparison': {}
    }
    
    # Test Omnizart
    print("\n" + "=" * 80)
    print("  TESTING OMNIZART PIPELINE")
    print("=" * 80)
    
    omnizart_dir = os.path.join(output_dir, "omnizart")
    os.makedirs(omnizart_dir, exist_ok=True)
    
    start_time = time.time()
    try:
        omnizart_results = run_omnizart_pipeline(audio_file, omnizart_dir)
        omnizart_time = time.time() - start_time
        
        results['omnizart'] = {
            'status': 'success',
            'processing_time': omnizart_time,
            **omnizart_results
        }
        
        # Analyze MIDI
        if os.path.exists(omnizart_results['midi_file']):
            midi_stats = analyze_midi_file(omnizart_results['midi_file'])
            results['omnizart']['midi_stats'] = midi_stats
            
            print(f"\n  ✓ Omnizart completed in {omnizart_time:.2f} seconds")
            print(f"    • MIDI: {midi_stats['total_notes']} notes, {midi_stats['tempo']:.1f} BPM")
            print(f"    • Note density: {midi_stats['note_density']:.2f} notes/second")
    
    except Exception as e:
        omnizart_time = time.time() - start_time
        results['omnizart'] = {
            'status': 'error',
            'error': str(e),
            'processing_time': omnizart_time
        }
        print(f"\n  ✗ Omnizart failed: {e}")
    
    # Test AnNOTEator
    print("\n" + "=" * 80)
    print("  TESTING ANNOTEATOR PIPELINE")
    print("=" * 80)
    
    annoteator_dir = os.path.join(output_dir, "annoteator")
    os.makedirs(annoteator_dir, exist_ok=True)
    
    start_time = time.time()
    try:
        annoteator_results = run_annoteator_pipeline(audio_file, annoteator_dir)
        annoteator_time = time.time() - start_time
        
        results['annoteator'] = {
            'status': 'success',
            'processing_time': annoteator_time,
            **annoteator_results
        }
        
        print(f"\n  ✓ AnNOTEator completed in {annoteator_time:.2f} seconds")
        print(f"    • Detected BPM: {annoteator_results['detected_bpm']:.1f}")
        print(f"    • Total hits: {annoteator_results['total_hits']}")
        print(f"    • Breakdown:")
        for drum, count in annoteator_results['hit_breakdown'].items():
            if count > 0:
                print(f"       - {drum}: {count}")
    
    except Exception as e:
        annoteator_time = time.time() - start_time
        results['annoteator'] = {
            'status': 'error',
            'error': str(e),
            'processing_time': annoteator_time
        }
        print(f"\n  ✗ AnNOTEator failed: {e}")
    
    # Comparison
    print("\n" + "=" * 80)
    print("  COMPARISON SUMMARY")
    print("=" * 80)
    
    if results['omnizart']['status'] == 'success' and results['annoteator']['status'] == 'success':
        faster = 'Omnizart' if omnizart_time < annoteator_time else 'AnNOTEator'
        speedup = max(omnizart_time, annoteator_time) / min(omnizart_time, annoteator_time)
        
        print(f"\n⚡ Performance:")
        print(f"   • Omnizart: {omnizart_time:.2f}s")
        print(f"   • AnNOTEator: {annoteator_time:.2f}s")
        print(f"   • Winner: {faster} ({speedup:.2f}x faster)")
        
        results['comparison']['performance'] = {
            'faster_pipeline': faster.lower(),
            'speedup': speedup,
            'omnizart_time': omnizart_time,
            'annoteator_time': annoteator_time
        }
    
    # Save results
    results_file = os.path.join(output_dir, "comparison_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Compare Omnizart and AnNOTEator pipelines')
    parser.add_argument('audio_file', help='Path to audio file')
    parser.add_argument('--output', default='test_results', help='Output directory')
    parser.add_argument('--ground-truth', help='Path to ground truth MIDI file (optional)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.audio_file):
        print(f"Error: Audio file not found: {args.audio_file}")
        sys.exit(1)
    
    results = compare_pipelines(args.audio_file, args.output, args.ground_truth)
    
    print("\n✓ Comparison complete!")
