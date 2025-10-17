# Drum Transcription Pipeline Testing & Improvement Plan

## Overview
This document outlines a comprehensive testing and improvement strategy for two drum transcription pipelines:
1. **Omnizart Pipeline**: Audio → MIDI → MusicXML
2. **AnNOTEator Pipeline**: Audio → MusicXML (direct)

---

## Table of Contents
1. [Test Dataset Preparation](#test-dataset-preparation)
2. [Evaluation Metrics](#evaluation-metrics)
3. [Pipeline Testing Procedures](#pipeline-testing-procedures)
4. [Improvement Strategies](#improvement-strategies)
5. [Resource Requirements](#resource-requirements)
6. [Step-by-Step Execution Plan](#step-by-step-execution-plan)

---

## 1. Test Dataset Preparation

### 1.1 Ground Truth Dataset Creation
**Goal**: Create a reference dataset with known, verified drum patterns

#### Option A: Use Existing Drum MIDI Datasets
- **E-GMD Dataset** (Expanded Groove MIDI Dataset)
  - Already available in `AnNOTEator/dataset/e-gmd-v1.0.0/`
  - Contains human-performed drum tracks with MIDI ground truth
  - Convert MIDI → Audio → Test both pipelines → Compare output to original MIDI
  
- **ENST-Drums Dataset**
  - Professional drummer recordings with annotations
  - Multiple drum kit configurations
  - Download: http://www.tsi.telecom-paristech.fr/aao/en/2010/02/19/enst-drums-an-extensive-audio-visual-database-for-drum-signals-processing/

- **MusicNet Dataset** (drum portions)
  - Classical music with MIDI ground truth
  - More complex rhythms and patterns

#### Option B: Create Custom Test Set
1. **Simple Patterns** (10-20 samples)
   - Basic rock beats (kick-snare-hihat)
   - Different tempos: 60, 90, 120, 150, 180 BPM
   - Known time signatures: 4/4, 3/4, 6/8

2. **Intermediate Patterns** (10-20 samples)
   - Fills and breaks
   - Ghost notes on snare
   - Hi-hat variations (open/closed)
   - Tom patterns

3. **Complex Patterns** (10-20 samples)
   - Polyrhythms
   - Fast double bass
   - Jazz patterns with ride/cymbal work
   - Multi-hit simultaneous drums

4. **Genre-Specific** (20-30 samples)
   - Rock: AC/DC, Led Zeppelin style
   - Metal: Double bass, blast beats
   - Jazz: Swing patterns, brushes
   - Funk: Syncopated grooves
   - Pop: Simple, consistent patterns

#### Action Items:
```bash
# Create test dataset directory structure
mkdir test_datasets
mkdir test_datasets/ground_truth
mkdir test_datasets/simple_patterns
mkdir test_datasets/intermediate_patterns
mkdir test_datasets/complex_patterns
mkdir test_datasets/genre_specific
mkdir test_datasets/results
```

### 1.2 Audio Quality Variations
Test both pipelines with different audio conditions:
- **Clean studio recordings** (isolated drums)
- **Demixed tracks** (Demucs-processed from full songs)
- **Different audio formats**: WAV (44.1kHz, 48kHz), MP3 (320kbps, 128kbps)
- **With/without compression effects**
- **Different recording qualities**: Studio → Live → Demo quality

---

## 2. Evaluation Metrics

### 2.1 Onset Detection Metrics
**Measure how well each pipeline detects drum hits**

#### Metrics to Calculate:
1. **Precision**: TP / (TP + FP)
   - How many detected hits were correct?
   
2. **Recall**: TP / (TP + FN)
   - How many actual hits were detected?
   
3. **F1-Score**: 2 × (Precision × Recall) / (Precision + Recall)
   - Overall accuracy balance

4. **Onset Detection Function (ODF) Accuracy**
   - Timing accuracy within tolerance windows:
     - Strict: ±25ms
     - Moderate: ±50ms
     - Loose: ±100ms

#### Implementation:
```python
# Create evaluation script: evaluate_onset_detection.py
import pretty_midi
import numpy as np

def calculate_onset_metrics(ground_truth_midi, predicted_midi, tolerance_ms=50):
    """
    Compare predicted onsets against ground truth
    """
    # Extract onsets from both MIDI files
    gt_onsets = extract_onsets(ground_truth_midi)
    pred_onsets = extract_onsets(predicted_midi)
    
    # Match onsets within tolerance
    tolerance_sec = tolerance_ms / 1000.0
    tp, fp, fn = match_onsets(gt_onsets, pred_onsets, tolerance_sec)
    
    # Calculate metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'true_positives': tp,
        'false_positives': fp,
        'false_negatives': fn
    }
```

### 2.2 Instrument Classification Metrics
**Measure how well each pipeline identifies drum types**

#### Per-Instrument Metrics:
- Kick/Bass Drum accuracy
- Snare Drum accuracy
- Hi-Hat accuracy (open vs closed)
- Tom-Toms accuracy
- Cymbals (Ride, Crash) accuracy

#### Confusion Matrix:
Create confusion matrices to see misclassification patterns
- Example: How often is kick misclassified as floor tom?

### 2.3 Rhythm Accuracy Metrics
**Measure how well rhythmic patterns are captured**

1. **Note Duration Accuracy**
   - Compare quarter notes, eighth notes, sixteenth notes, triplets
   - Measure quantization errors

2. **Tempo Stability**
   - Check if detected BPM matches ground truth
   - Measure tempo drift over time

3. **Time Signature Detection**
   - Verify correct measure boundaries
   - Check handling of time signature changes

### 2.4 MusicXML Quality Metrics
**Measure notation quality**

1. **Readability Score** (subjective, but important)
   - Are notes properly quantized?
   - Are rests appropriately placed?
   - Is the notation human-readable?

2. **Notation Correctness**
   - Correct noteheads (normal vs x-shaped for cymbals)
   - Correct staff positions
   - Proper clef (percussion clef)
   - Correct MIDI channel (channel 10)

3. **File Size and Complexity**
   - MusicXML file size
   - Number of measures generated
   - Notation density (notes per measure)

### 2.5 Performance Metrics
**Measure computational efficiency**

1. **Processing Time**
   - Time to process 1 minute of audio
   - Time to process 5 minutes of audio
   - Scalability to longer tracks

2. **Memory Usage**
   - Peak RAM consumption
   - GPU memory usage (if applicable)

3. **Resource Requirements**
   - CPU cores utilized
   - Disk I/O requirements

---

## 3. Pipeline Testing Procedures

### 3.1 Omnizart Pipeline Testing

#### Current Omnizart Configurations to Test:

**Configuration 1: Standard 3-Class (Baseline)**
```python
# Script: test_omnizart_baseline.py
from omnizart.drum import app as drum_app

# Test with default settings
drum_app.transcribe(
    audio_path="test_audio.wav",
    model_path=None,  # Use default model
    output="output.mid"
)
```

**Configuration 2: Custom 6-Class Grouping**
```python
# Script: test_omnizart_6classes.py
# Your existing test_omnizart_6_classes.py with custom grouping:
# - Kick, Snare, Hi-Hat, Toms, Ride, Crash
```

**Configuration 3: All 13 Classes (Full Detail)**
```python
# Script: test_omnizart_13classes.py
# Use all Omnizart drum classes without grouping
```

**Configuration 4: Tempo Variations**
```python
# Test BPM detection accuracy
# Pre-process audio with known tempo changes
```

#### Omnizart Parameters to Tune:
1. **Threshold Settings**
   - Adjust onset detection thresholds
   - Test different confidence thresholds for classification

2. **Post-Processing**
   - Non-maximum suppression window size
   - Minimum note duration filtering

3. **Model Selection**
   - Test if multiple Omnizart models exist
   - Compare drum-specific vs general models

### 3.2 AnNOTEator Pipeline Testing

#### Current AnNOTEator Model to Test:

**Model: complete_network**
- Currently available and working
- Detects: SD, HH, KD, RC, TT, CC

#### AnNOTEator Parameters to Test:

**1. Resolution Parameter**
```python
# Script: test_annoteator_resolutions.py
resolutions = [None, 8, 16, 32]

for res in resolutions:
    frames, bpm = drum_to_frame(audio, sr, estimated_bpm=None, resolution=res)
    df = predict_drumhit(model_path, frames, sr)
    # Evaluate results
```

**2. BPM Estimation**
```python
# Test with known BPM vs auto-detection
known_bpms = [60, 90, 120, 150, 180]

for bpm in known_bpms:
    frames, detected_bpm = drum_to_frame(audio, sr, estimated_bpm=bpm, resolution=16)
    # Compare detected_bpm to known value
```

**3. Note Offset Calibration**
```python
# Test different note_offset values
offsets = [None, 0, 1, 2, 3, 4, 5]

for offset in offsets:
    transcriber = drum_transcriber(
        df, duration, bpm, sr,
        note_offset=offset
    )
    # Evaluate alignment accuracy
```

### 3.3 Comparative Testing Script

Create a unified testing script that runs both pipelines on the same input:

```python
# Script: compare_pipelines.py

import os
import time
import json
from datetime import datetime

def test_both_pipelines(audio_file, ground_truth_midi=None):
    """
    Run both Omnizart and AnNOTEator on the same audio file
    Compare results and performance
    """
    results = {
        'audio_file': audio_file,
        'timestamp': datetime.now().isoformat(),
        'omnizart': {},
        'annoteator': {},
        'comparison': {}
    }
    
    # Test Omnizart Pipeline
    print("Testing Omnizart Pipeline...")
    start_time = time.time()
    try:
        omnizart_midi, omnizart_xml = run_omnizart_pipeline(audio_file)
        results['omnizart'] = {
            'status': 'success',
            'processing_time': time.time() - start_time,
            'midi_file': omnizart_midi,
            'xml_file': omnizart_xml,
            'midi_stats': analyze_midi(omnizart_midi)
        }
    except Exception as e:
        results['omnizart'] = {
            'status': 'error',
            'error': str(e),
            'processing_time': time.time() - start_time
        }
    
    # Test AnNOTEator Pipeline
    print("Testing AnNOTEator Pipeline...")
    start_time = time.time()
    try:
        annoteator_xml = run_annoteator_pipeline(audio_file)
        results['annoteator'] = {
            'status': 'success',
            'processing_time': time.time() - start_time,
            'xml_file': annoteator_xml,
            'xml_stats': analyze_musicxml(annoteator_xml)
        }
    except Exception as e:
        results['annoteator'] = {
            'status': 'error',
            'error': str(e),
            'processing_time': time.time() - start_time
        }
    
    # Compare against ground truth if available
    if ground_truth_midi and results['omnizart']['status'] == 'success':
        results['comparison']['omnizart_accuracy'] = calculate_onset_metrics(
            ground_truth_midi, 
            results['omnizart']['midi_file']
        )
    
    # Save results
    output_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    return results
```

---

## 4. Improvement Strategies

### 4.1 AnNOTEator Improvements (Based on Known Issues)

#### Issue 1: Multi-Hit Label Underperformance
**Problem**: Model struggles when multiple drums are hit simultaneously (~80% training data is single-label)

**Solutions to Test**:

1. **Increase Multi-Hit Threshold**
   ```python
   # Modify data_preparation.py or training script
   # Current: 0.02 seconds (20ms)
   # Test: 0.03, 0.05, 0.1 seconds
   
   MULTI_HIT_THRESHOLD = 0.05  # 50ms window
   ```

2. **Generate Synthetic Multi-Hit Training Data**
   ```python
   # Script: augment_multihit_training.py
   
   def create_synthetic_multihits(single_hit_samples):
       """
       Combine single-hit samples to create multi-hit training data
       """
       # Mix kick + snare samples
       # Mix hi-hat + kick samples
       # Mix complex 3+ instrument combinations
       pass
   ```

3. **Post-Processing Multi-Hit Detection**
   ```python
   # Add multi-hit detection logic after prediction
   def merge_simultaneous_hits(predictions, window_ms=25):
       """
       Merge predictions that occur within a time window
       """
       pass
   ```

#### Issue 2: Quantization and Time Mapping Inaccuracy
**Problem**: Sensitive to exact timing, human delay causes misclassification (triplet → 16th note)

**Solutions to Test**:

1. **Implement Hidden Markov Model (HMM)**
   ```python
   # Script: hmm_rhythm_correction.py
   from hmmlearn import hmm
   
   class RhythmHMM:
       """
       Use HMM to correct note duration predictions based on:
       - Musical context (previous notes)
       - Tempo consistency
       - Common rhythmic patterns
       """
       def __init__(self, n_states=4):
           # States: quarter, eighth, sixteenth, triplet
           self.model = hmm.GaussianHMM(n_components=n_states)
       
       def train(self, correct_sequences):
           """Train on known-correct rhythm sequences"""
           pass
       
       def correct_rhythm(self, predicted_sequence):
           """Apply HMM to correct predicted rhythms"""
           pass
   ```

2. **Fuzzy Quantization**
   ```python
   # Instead of hard quantization, use probabilistic approach
   def fuzzy_quantize(onset_time, grid_divisions=[4, 8, 16, 24]):
       """
       Calculate probability of each grid division
       Choose most likely based on musical context
       """
       pass
   ```

3. **Adaptive Quantization Grid**
   ```python
   # Adjust quantization grid based on detected tempo and genre
   def adaptive_grid(bpm, genre_hint=None):
       if bpm > 180:  # Fast tempo
           return [8, 16, 32]  # Prefer simpler divisions
       elif bpm < 70:  # Slow tempo
           return [4, 8, 16, 24, 32]  # Allow more complex divisions
       else:
           return [4, 8, 12, 16, 24]  # Standard
   ```

#### Issue 3: Demucs Processing Effects ⚠️ **CRITICAL - HIGH PRIORITY**
**Problem**: Training data doesn't match Demucs-processed audio characteristics

**Why This Matters**:
The AnNOTEator team identified this as a major issue. In production, GrooveSheet will use Demucs to extract drum tracks from full songs. However, AnNOTEator was trained on clean, isolated drum recordings. Demucs applies various filters and effects during source separation that change the audio characteristics:
- Spectral filtering to isolate drums
- Artifact introduction from neural separation
- Frequency response changes
- Phase alterations
- Dynamic range modifications

**This mismatch means the model sees very different audio in production vs. training, leading to reduced accuracy.**

**Solutions to Test** (Resource-Intensive but Essential):

1. **Reprocess ALL Training Data with Demucs** ⭐ **RECOMMENDED APPROACH**
   
   This is the most logical and effective solution. Process the entire E-GMD dataset through Demucs to make training data match production data.
   
   ```bash
   # Script: reprocess_training_with_demucs.sh
   
   #!/bin/bash
   # Demucs Training Data Reprocessing Pipeline
   # WARNING: This is EXTREMELY resource-intensive
   # Estimated time: 20-40 hours on high-end workstation
   # Estimated storage: 200-300 GB for processed audio
   
   INPUT_DIR="AnNOTEator/dataset/e-gmd-v1.0.0"
   OUTPUT_DIR="training_data/demucs_processed"
   DEMUCS_MODEL="htdemucs"  # Latest and best model
   
   echo "Starting Demucs processing of E-GMD dataset..."
   echo "Input:  $INPUT_DIR"
   echo "Output: $OUTPUT_DIR"
   echo "Model:  $DEMUCS_MODEL"
   echo ""
   echo "WARNING: This will take 20-40 hours and use significant disk space"
   echo "Press Ctrl+C to cancel, or wait 10 seconds to continue..."
   sleep 10
   
   # Create output directory
   mkdir -p "$OUTPUT_DIR"
   
   # Count total files for progress tracking
   TOTAL_FILES=$(find "$INPUT_DIR" -name "*.wav" | wc -l)
   CURRENT=0
   
   echo "Found $TOTAL_FILES audio files to process"
   echo ""
   
   # Process each WAV file in E-GMD dataset
   find "$INPUT_DIR" -name "*.wav" | while read audio_file; do
       CURRENT=$((CURRENT + 1))
       
       # Get relative path to maintain directory structure
       REL_PATH="${audio_file#$INPUT_DIR/}"
       OUTPUT_SUBDIR="$OUTPUT_DIR/$(dirname "$REL_PATH")"
       
       mkdir -p "$OUTPUT_SUBDIR"
       
       echo "[$CURRENT/$TOTAL_FILES] Processing: $(basename "$audio_file")"
       
       # Run Demucs - extract only drums stem
       # --two-stems=drums: Only separate drums (faster than 4-stem)
       # -n htdemucs: Use latest hybrid transformer model
       # --mp3: Save as MP3 to save disk space (optional, use --flac for lossless)
       # --mp3-bitrate 320: High quality MP3
       demucs --two-stems=drums \
              -n "$DEMUCS_MODEL" \
              --mp3 \
              --mp3-bitrate 320 \
              -o "$OUTPUT_SUBDIR" \
              "$audio_file"
       
       # Demucs creates subdirectory structure: htdemucs/<filename>/drums.mp3
       # Move and rename to match original structure
       BASENAME=$(basename "$audio_file" .wav)
       mv "$OUTPUT_SUBDIR/$DEMUCS_MODEL/$BASENAME/drums.mp3" \
          "$OUTPUT_SUBDIR/${BASENAME}_drums.mp3"
       
       # Clean up Demucs temporary directories
       rm -rf "$OUTPUT_SUBDIR/$DEMUCS_MODEL"
       
       echo "  ✓ Saved to: $OUTPUT_SUBDIR/${BASENAME}_drums.mp3"
   done
   
   echo ""
   echo "✓ Demucs processing complete!"
   echo "Processed audio saved to: $OUTPUT_DIR"
   ```
   
   **PowerShell version for Windows:**
   ```powershell
   # reprocess_training_with_demucs.ps1
   
   $INPUT_DIR = "AnNOTEator/dataset/e-gmd-v1.0.0"
   $OUTPUT_DIR = "training_data/demucs_processed"
   $DEMUCS_MODEL = "htdemucs"
   
   Write-Host "Starting Demucs processing of E-GMD dataset..." -ForegroundColor Green
   Write-Host "WARNING: This will take 20-40 hours and use significant disk space"
   Write-Host "Press Ctrl+C to cancel, or wait 10 seconds to continue..."
   Start-Sleep -Seconds 10
   
   # Create output directory
   New-Item -ItemType Directory -Force -Path $OUTPUT_DIR | Out-Null
   
   # Get all WAV files
   $files = Get-ChildItem -Path $INPUT_DIR -Filter "*.wav" -Recurse
   $total = $files.Count
   $current = 0
   
   Write-Host "Found $total audio files to process`n"
   
   foreach ($file in $files) {
       $current++
       
       # Calculate relative path
       $relPath = $file.FullName.Substring($INPUT_DIR.Length + 1)
       $outputSubDir = Join-Path $OUTPUT_DIR (Split-Path $relPath)
       
       New-Item -ItemType Directory -Force -Path $outputSubDir | Out-Null
       
       Write-Host "[$current/$total] Processing: $($file.Name)" -ForegroundColor Cyan
       
       # Run Demucs
       & demucs --two-stems=drums `
                -n $DEMUCS_MODEL `
                --mp3 `
                --mp3-bitrate 320 `
                -o $outputSubDir `
                $file.FullName
       
       # Move and rename output
       $basename = $file.BaseName
       $demucsPart = Join-Path $outputSubDir "$DEMUCS_MODEL\$basename\drums.mp3"
       $finalPath = Join-Path $outputSubDir "${basename}_drums.mp3"
       
       Move-Item -Path $demucsPart -Destination $finalPath -Force
       Remove-Item -Path (Join-Path $outputSubDir $DEMUCS_MODEL) -Recurse -Force
       
       Write-Host "  ✓ Saved to: $finalPath" -ForegroundColor Green
   }
   
   Write-Host "`n✓ Demucs processing complete!" -ForegroundColor Green
   ```
   
   **Python version (more cross-platform):**
   ```python
   # Script: reprocess_training_with_demucs.py
   
   import os
   import subprocess
   from pathlib import Path
   from tqdm import tqdm
   import shutil
   
   def process_with_demucs(input_dir, output_dir, model_name="htdemucs"):
       """
       Process all WAV files in input_dir through Demucs
       
       Args:
           input_dir: Directory containing training audio files
           output_dir: Directory to save Demucs-processed audio
           model_name: Demucs model to use (htdemucs recommended)
       """
       input_path = Path(input_dir)
       output_path = Path(output_dir)
       output_path.mkdir(parents=True, exist_ok=True)
       
       # Find all WAV files
       wav_files = list(input_path.rglob("*.wav"))
       
       print(f"Found {len(wav_files)} audio files to process")
       print(f"Model: {model_name}")
       print(f"Output: {output_dir}")
       print("\nWARNING: This will take 20-40 hours")
       print("Press Ctrl+C to cancel within 10 seconds...")
       
       import time
       time.sleep(10)
       
       # Process each file
       for i, wav_file in enumerate(tqdm(wav_files, desc="Processing")):
           # Calculate relative path
           rel_path = wav_file.relative_to(input_path)
           output_subdir = output_path / rel_path.parent
           output_subdir.mkdir(parents=True, exist_ok=True)
           
           # Run Demucs
           try:
               subprocess.run([
                   "demucs",
                   "--two-stems=drums",
                   "-n", model_name,
                   "--mp3",
                   "--mp3-bitrate", "320",
                   "-o", str(output_subdir),
                   str(wav_file)
               ], check=True, capture_output=True)
               
               # Move output to final location
               demucs_output = output_subdir / model_name / wav_file.stem / "drums.mp3"
               final_output = output_subdir / f"{wav_file.stem}_drums.mp3"
               
               if demucs_output.exists():
                   shutil.move(str(demucs_output), str(final_output))
                   # Clean up Demucs temp directories
                   shutil.rmtree(output_subdir / model_name)
                   
                   print(f"✓ [{i+1}/{len(wav_files)}] {wav_file.name} -> {final_output.name}")
               else:
                   print(f"✗ [{i+1}/{len(wav_files)}] Failed: {wav_file.name}")
                   
           except subprocess.CalledProcessError as e:
               print(f"✗ Error processing {wav_file.name}: {e}")
               continue
       
       print(f"\n✓ Processing complete! Output saved to: {output_dir}")
   
   if __name__ == "__main__":
       import argparse
       
       parser = argparse.ArgumentParser(description='Process training data with Demucs')
       parser.add_argument('--input', default='AnNOTEator/dataset/e-gmd-v1.0.0',
                          help='Input directory with training audio')
       parser.add_argument('--output', default='training_data/demucs_processed',
                          help='Output directory for processed audio')
       parser.add_argument('--model', default='htdemucs',
                          choices=['htdemucs', 'htdemucs_ft', 'mdx_extra'],
                          help='Demucs model to use')
       
       args = parser.parse_args()
       
       process_with_demucs(args.input, args.output, args.model)
   ```
   
   **After Demucs processing, retrain the model:**
   ```bash
   # Retrain AnNOTEator with Demucs-processed audio
   python AnNOTEator/model_development/train_model.py \
       --dataset training_data/demucs_processed/ \
       --model_name complete_network_demucs \
       --epochs 100 \
       --batch_size 32 \
       --learning_rate 0.001
   
   # This will take 24-72 hours depending on hardware
   ```

2. **Analyze Demucs Audio Characteristics**
   
   Before retraining, understand what Demucs does to the audio:
   
   ```python
   # Script: analyze_demucs_effects.py
   
   import librosa
   import numpy as np
   import matplotlib.pyplot as plt
   from scipy import signal
   
   def analyze_audio_characteristics(original_path, demucs_processed_path):
       """
       Compare spectral characteristics between original and Demucs-processed audio
       This helps understand what effects Demucs applies
       """
       # Load both versions
       original, sr_orig = librosa.load(original_path, sr=None)
       processed, sr_proc = librosa.load(demucs_processed_path, sr=None)
       
       # Resample if needed
       if sr_orig != sr_proc:
           processed = librosa.resample(processed, orig_sr=sr_proc, target_sr=sr_orig)
       
       results = {
           'original_file': original_path,
           'processed_file': demucs_processed_path,
           'sample_rate': sr_orig,
           'analysis': {}
       }
       
       # 1. Frequency Response Analysis
       print("\n📊 Analyzing Frequency Response...")
       orig_fft = np.fft.fft(original)
       proc_fft = np.fft.fft(processed)
       
       freqs = np.fft.fftfreq(len(original), 1/sr_orig)
       
       # Compare magnitude spectra
       orig_mag = np.abs(orig_fft)
       proc_mag = np.abs(proc_fft)
       
       # Calculate frequency response difference
       freq_diff = 20 * np.log10(proc_mag / (orig_mag + 1e-10))
       
       results['analysis']['frequency_response'] = {
           'mean_difference_db': float(np.mean(freq_diff[freqs > 0])),
           'std_difference_db': float(np.std(freq_diff[freqs > 0]))
       }
       
       # 2. Spectral Centroid (brightness)
       print("📊 Analyzing Spectral Centroid...")
       orig_centroid = librosa.feature.spectral_centroid(y=original, sr=sr_orig)[0]
       proc_centroid = librosa.feature.spectral_centroid(y=processed, sr=sr_orig)[0]
       
       results['analysis']['spectral_centroid'] = {
           'original_mean': float(np.mean(orig_centroid)),
           'processed_mean': float(np.mean(proc_centroid)),
           'difference_hz': float(np.mean(proc_centroid) - np.mean(orig_centroid))
       }
       
       # 3. Zero-Crossing Rate (noisiness)
       print("📊 Analyzing Zero-Crossing Rate...")
       orig_zcr = librosa.feature.zero_crossing_rate(original)[0]
       proc_zcr = librosa.feature.zero_crossing_rate(processed)[0]
       
       results['analysis']['zero_crossing_rate'] = {
           'original_mean': float(np.mean(orig_zcr)),
           'processed_mean': float(np.mean(proc_zcr)),
           'difference': float(np.mean(proc_zcr) - np.mean(orig_zcr))
       }
       
       # 4. Dynamic Range
       print("📊 Analyzing Dynamic Range...")
       orig_rms = librosa.feature.rms(y=original)[0]
       proc_rms = librosa.feature.rms(y=processed)[0]
       
       orig_db = librosa.amplitude_to_db(orig_rms, ref=np.max)
       proc_db = librosa.amplitude_to_db(proc_rms, ref=np.max)
       
       results['analysis']['dynamic_range'] = {
           'original_range_db': float(np.max(orig_db) - np.min(orig_db)),
           'processed_range_db': float(np.max(proc_db) - np.min(proc_db)),
           'compression': float((np.max(orig_db) - np.min(orig_db)) - (np.max(proc_db) - np.min(proc_db)))
       }
       
       # 5. MFCC Comparison (timbre)
       print("📊 Analyzing MFCCs (timbre)...")
       orig_mfcc = librosa.feature.mfcc(y=original, sr=sr_orig, n_mfcc=13)
       proc_mfcc = librosa.feature.mfcc(y=processed, sr=sr_orig, n_mfcc=13)
       
       mfcc_diff = np.mean(np.abs(orig_mfcc - proc_mfcc), axis=1)
       
       results['analysis']['mfcc'] = {
           'mean_difference': float(np.mean(mfcc_diff)),
           'per_coefficient': mfcc_diff.tolist()
       }
       
       # 6. Harmonic-Percussive Separation
       print("📊 Analyzing Harmonic vs Percussive Content...")
       orig_harmonic, orig_percussive = librosa.effects.hpss(original)
       proc_harmonic, proc_percussive = librosa.effects.hpss(processed)
       
       results['analysis']['harmonic_percussive'] = {
           'original_percussive_ratio': float(np.mean(np.abs(orig_percussive)) / (np.mean(np.abs(original)) + 1e-10)),
           'processed_percussive_ratio': float(np.mean(np.abs(proc_percussive)) / (np.mean(np.abs(processed)) + 1e-10))
       }
       
       # 7. Artifacts Detection (check for separation artifacts)
       print("📊 Detecting Potential Artifacts...")
       
       # High-frequency noise check
       proc_high_freq = librosa.stft(processed)
       high_freq_energy = np.mean(np.abs(proc_high_freq[int(len(proc_high_freq)*0.8):, :]))
       
       results['analysis']['artifacts'] = {
           'high_freq_energy': float(high_freq_energy),
           'potential_artifacts': high_freq_energy > 0.1  # Threshold for artifact detection
       }
       
       print("\n✓ Analysis complete!")
       
       return results
   
   def visualize_comparison(original_path, demucs_processed_path, output_file="demucs_comparison.png"):
       """
       Create visualization comparing original and Demucs-processed audio
       """
       original, sr = librosa.load(original_path, sr=None)
       processed, _ = librosa.load(demucs_processed_path, sr=sr)
       
       fig, axes = plt.subplots(3, 2, figsize=(15, 10))
       fig.suptitle('Original vs Demucs-Processed Audio Comparison', fontsize=16)
       
       # Waveforms
       axes[0, 0].plot(original[:sr*5])  # First 5 seconds
       axes[0, 0].set_title('Original Waveform')
       axes[0, 0].set_xlabel('Samples')
       
       axes[0, 1].plot(processed[:sr*5])
       axes[0, 1].set_title('Demucs-Processed Waveform')
       axes[0, 1].set_xlabel('Samples')
       
       # Spectrograms
       orig_spec = librosa.amplitude_to_db(np.abs(librosa.stft(original)), ref=np.max)
       proc_spec = librosa.amplitude_to_db(np.abs(librosa.stft(processed)), ref=np.max)
       
       librosa.display.specshow(orig_spec, sr=sr, x_axis='time', y_axis='hz', ax=axes[1, 0])
       axes[1, 0].set_title('Original Spectrogram')
       
       librosa.display.specshow(proc_spec, sr=sr, x_axis='time', y_axis='hz', ax=axes[1, 1])
       axes[1, 1].set_title('Demucs-Processed Spectrogram')
       
       # Difference Spectrogram
       diff_spec = proc_spec - orig_spec
       im = librosa.display.specshow(diff_spec, sr=sr, x_axis='time', y_axis='hz', 
                                      ax=axes[2, 0], cmap='RdBu_r')
       axes[2, 0].set_title('Difference (Processed - Original)')
       plt.colorbar(im, ax=axes[2, 0])
       
       # Frequency Response
       freqs = np.fft.fftfreq(len(original), 1/sr)
       orig_fft = np.abs(np.fft.fft(original))
       proc_fft = np.abs(np.fft.fft(processed))
       
       pos_freqs = freqs > 0
       axes[2, 1].semilogx(freqs[pos_freqs], 20*np.log10(orig_fft[pos_freqs]), label='Original', alpha=0.7)
       axes[2, 1].semilogx(freqs[pos_freqs], 20*np.log10(proc_fft[pos_freqs]), label='Processed', alpha=0.7)
       axes[2, 1].set_title('Frequency Response')
       axes[2, 1].set_xlabel('Frequency (Hz)')
       axes[2, 1].set_ylabel('Magnitude (dB)')
       axes[2, 1].legend()
       axes[2, 1].grid(True)
       
       plt.tight_layout()
       plt.savefig(output_file, dpi=150)
       print(f"✓ Visualization saved to: {output_file}")
   
   if __name__ == "__main__":
       import argparse
       import json
       
       parser = argparse.ArgumentParser(description='Analyze Demucs audio effects')
       parser.add_argument('--original', required=True, help='Original audio file')
       parser.add_argument('--processed', required=True, help='Demucs-processed audio file')
       parser.add_argument('--output-json', default='demucs_analysis.json', help='Output JSON file')
       parser.add_argument('--output-plot', default='demucs_comparison.png', help='Output plot file')
       
       args = parser.parse_args()
       
       # Analyze
       results = analyze_audio_characteristics(args.original, args.processed)
       
       # Save results
       with open(args.output_json, 'w') as f:
           json.dump(results, f, indent=2)
       
       print(f"\n💾 Analysis saved to: {args.output_json}")
       
       # Visualize
       visualize_comparison(args.original, args.processed, args.output_plot)
   ```

3. **Apply Demucs-Like Effects to Training** (Alternative if reprocessing is too expensive)
   
   If full Demucs reprocessing is too resource-intensive, simulate its effects:
   
   ```python
   # Script: apply_demucs_simulation.py
   
   import librosa
   import numpy as np
   import soundfile as sf
   from scipy import signal
   
   def simulate_demucs_processing(audio, sr, analysis_results):
       """
       Apply filters/effects that mimic Demucs output based on analysis
       
       This is a cheaper alternative to full Demucs processing
       Uses insights from analyze_demucs_effects.py
       """
       processed = audio.copy()
       
       # 1. Band-pass filter (Demucs tends to filter extreme frequencies)
       # Keep 40Hz - 16kHz (typical drum range with some safety margin)
       sos = signal.butter(4, [40, 16000], btype='bandpass', fs=sr, output='sos')
       processed = signal.sosfilt(sos, processed)
       
       # 2. Spectral gate (reduce noise floor, simulate separation artifacts)
       stft = librosa.stft(processed)
       mag = np.abs(stft)
       phase = np.angle(stft)
       
       # Apply soft gate
       threshold = np.percentile(mag, 20)  # Adjust based on analysis
       gate = np.maximum(0, (mag - threshold) / mag)
       stft_gated = mag * gate * np.exp(1j * phase)
       
       processed = librosa.istft(stft_gated)
       
       # 3. Transient enhancement (Demucs sharpens drum hits)
       # Harmonic-percussive separation
       harmonic, percussive = librosa.effects.hpss(processed)
       
       # Enhance percussive component
       processed = harmonic * 0.3 + percussive * 1.2
       
       # 4. Slight compression (Demucs reduces dynamic range)
       # Simple soft limiting
       threshold_db = -6
       threshold_linear = 10 ** (threshold_db / 20)
       
       mask = np.abs(processed) > threshold_linear
       compressed = processed.copy()
       compressed[mask] = np.sign(processed[mask]) * (
           threshold_linear + (np.abs(processed[mask]) - threshold_linear) * 0.5
       )
       
       processed = compressed
       
       # 5. Normalize
       processed = processed / (np.max(np.abs(processed)) + 1e-10) * 0.9
       
       return processed
   
   def batch_simulate_demucs(input_dir, output_dir, analysis_json):
       """
       Apply Demucs simulation to all training files
       """
       import json
       from pathlib import Path
       from tqdm import tqdm
       
       # Load analysis results
       with open(analysis_json, 'r') as f:
           analysis = json.load(f)
       
       input_path = Path(input_dir)
       output_path = Path(output_dir)
       output_path.mkdir(parents=True, exist_ok=True)
       
       wav_files = list(input_path.rglob("*.wav"))
       
       for wav_file in tqdm(wav_files, desc="Applying Demucs simulation"):
           # Load audio
           audio, sr = librosa.load(wav_file, sr=None, mono=True)
           
           # Apply simulation
           processed = simulate_demucs_processing(audio, sr, analysis)
           
           # Save
           rel_path = wav_file.relative_to(input_path)
           output_file = output_path / rel_path
           output_file.parent.mkdir(parents=True, exist_ok=True)
           
           sf.write(output_file, processed, sr)
       
       print(f"✓ Processed {len(wav_files)} files")
   ```

**Recommendation**: Option 1 (Full Demucs Reprocessing) is strongly recommended despite the resource cost. The AnNOTEator team explicitly states this is crucial for production performance. The time and computational investment will pay off with significantly better real-world accuracy.

#### Issue 4: Audio Augmentation Selection
**Problem**: Not enough testing of optimal augmentations for demixed audio

**Solutions to Test**:

1. **Systematic Augmentation Testing**
   ```python
   # Script: test_augmentations.py
   
   from audiomentations import (
       Compose, AddGaussianNoise, TimeStretch, PitchShift,
       Shift, Gain, PolarityInversion, BandPassFilter
   )
   
   # Test different augmentation combinations
   augmentation_configs = [
       # Config 1: Conservative
       Compose([
           AddGaussianNoise(min_amplitude=0.001, max_amplitude=0.005, p=0.3),
           Gain(min_gain_in_db=-3, max_gain_in_db=3, p=0.5)
       ]),
       
       # Config 2: Moderate
       Compose([
           AddGaussianNoise(min_amplitude=0.001, max_amplitude=0.01, p=0.5),
           TimeStretch(min_rate=0.95, max_rate=1.05, p=0.3),
           Gain(min_gain_in_db=-6, max_gain_in_db=6, p=0.5)
       ]),
       
       # Config 3: Aggressive
       Compose([
           AddGaussianNoise(min_amplitude=0.001, max_amplitude=0.015, p=0.5),
           TimeStretch(min_rate=0.9, max_rate=1.1, p=0.5),
           PitchShift(min_semitones=-1, max_semitones=1, p=0.3),
           BandPassFilter(min_center_freq=80, max_center_freq=8000, p=0.3),
           Gain(min_gain_in_db=-9, max_gain_in_db=9, p=0.5)
       ])
   ]
   
   # Train model with each config, evaluate performance
   ```

2. **Create Augmentation Grid Search**
   ```python
   # Hyperparameter tuning for augmentations
   augmentation_params = {
       'noise_level': [0.001, 0.005, 0.01, 0.015],
       'time_stretch': [0.95, 0.97, 1.0, 1.03, 1.05],
       'gain_db': [3, 6, 9, 12],
       'pitch_shift': [0, 0.5, 1.0],
   }
   
   # Test all combinations, rank by validation performance
   ```

### 4.2 Omnizart Improvements

#### Improvement 1: MIDI to MusicXML Conversion Quality
**Current Issue**: Rhythm quantization might be inaccurate

**Solutions**:

1. **Improve Quantization Algorithm**
   - Use the Fraction-based approach from your working converter
   - Add musical intelligence (prefer common patterns)

2. **Better Measure Organization**
   - Ensure proper measure boundaries
   - Handle pickup measures
   - Respect time signatures

3. **Note Duration Refinement**
   - Minimum note duration filtering
   - Connect short notes into longer ones when appropriate
   - Better rest placement

#### Improvement 2: Instrument Classification
**Test different class groupings**:

1. **Minimal (3 classes)**: Kick, Snare, Hi-Hat
2. **Standard (6 classes)**: Kick, Snare, Hi-Hat, Toms, Ride, Crash
3. **Detailed (13 classes)**: All Omnizart classes
4. **Custom grouping** based on your specific needs

#### Improvement 3: Ensemble Methods
**Combine multiple models**:

```python
# Script: omnizart_ensemble.py

def ensemble_predictions(predictions_list, voting='soft'):
    """
    Combine predictions from multiple Omnizart configurations
    - Different thresholds
    - Different class groupings
    - Vote on final prediction
    """
    pass
```

---

## 5. Resource Requirements

### 5.1 Computational Resources Needed

#### For Basic Testing (Your Current Setup):
- **RAM**: 8-16 GB
- **CPU**: 4+ cores
- **Storage**: 50-100 GB
- **Time**: 1-2 hours per test dataset

#### For Advanced Testing (Science Lab Setup):
- **RAM**: 32-64 GB (for large batch processing)
- **CPU**: 16+ cores
- **GPU**: NVIDIA GPU with 8+ GB VRAM (for retraining)
- **Storage**: 500 GB - 1 TB
  - Training data: ~200 GB
  - Processed audio: ~200 GB
  - Models and checkpoints: ~50 GB
  - Results and logs: ~50 GB
- **Time**: 
  - Full E-GMD Demucs processing: 20-40 hours
  - Model retraining: 24-72 hours per model
  - Full evaluation suite: 4-8 hours

### 5.2 Data Storage Structure

```
drumscore-testing/
├── datasets/
│   ├── ground_truth/          # Reference MIDI files
│   ├── audio_clean/           # Clean studio recordings
│   ├── audio_demixed/         # Demucs-processed tracks
│   ├── audio_compressed/      # Different quality levels
│   └── metadata.json          # Dataset information
├── models/
│   ├── annoteator/
│   │   ├── complete_network.h5
│   │   ├── complete_network_demucs.h5  # Retrained
│   │   └── specialized_models/
│   └── omnizart/
│       └── checkpoints/
├── results/
│   ├── omnizart/
│   │   ├── midi/
│   │   └── musicxml/
│   ├── annoteator/
│   │   └── musicxml/
│   └── metrics/
│       ├── onset_detection/
│       ├── instrument_classification/
│       └── rhythm_accuracy/
└── scripts/
    ├── preprocessing/
    ├── testing/
    ├── evaluation/
    └── analysis/
```

---

## 6. Step-by-Step Execution Plan

### Phase 1: Setup and Baseline (Week 1)

#### Day 1-2: Environment Setup
```bash
# 1. Clone and organize repositories
cd /path/to/science/lab/workspace
git clone <your-repo>
cd drumscore-be

# 2. Create conda environment
conda create -n drumscore python=3.8 -y
conda activate drumscore

# 3. Install dependencies
pip install -r requirements.txt
pip install omnizart
pip install audiomentations
pip install hmmlearn  # For HMM improvements

# 4. Download additional datasets
# E-GMD is already present
# Download ENST-Drums if needed
```

#### Day 3-4: Create Test Dataset
```bash
# 1. Organize existing audio files
python scripts/organize_test_dataset.py

# 2. Create ground truth MIDI files for custom tests
# Use MIDI editor to create simple patterns
# Save as: test_datasets/ground_truth/*.mid

# 3. Generate audio from MIDI using synthesizer
python scripts/midi_to_audio.py \
    --input test_datasets/ground_truth/ \
    --output test_datasets/audio_clean/

# 4. Process with Demucs
python scripts/process_with_demucs.py \
    --input test_datasets/audio_clean/ \
    --output test_datasets/audio_demixed/
```

#### Day 5-7: Baseline Testing
```bash
# 1. Run Omnizart baseline
python test_omnizart_baseline.py \
    --input test_datasets/audio_clean/ \
    --output results/omnizart/baseline/

# 2. Run AnNOTEator baseline
python annoteator_convert_baseline_wav_to_musicxml.py \
    --input test_datasets/audio_clean/ \
    --output results/annoteator/baseline/

# 3. Calculate baseline metrics
python scripts/evaluate_baseline.py \
    --ground_truth test_datasets/ground_truth/ \
    --omnizart_results results/omnizart/baseline/ \
    --annoteator_results results/annoteator/baseline/ \
    --output results/metrics/baseline_comparison.json
```

### Phase 2: Systematic Testing (Week 2-3)

#### Week 2: Parameter Tuning
```bash
# Day 1-2: AnNOTEator resolution testing
python test_annoteator_resolutions.py

# Day 3-4: AnNOTEator BPM testing
python test_annoteator_bpm.py

# Day 5-7: Omnizart class grouping testing
python test_omnizart_configurations.py
```

#### Week 3: Audio Condition Testing
```bash
# Day 1-2: Test with clean audio
python compare_pipelines.py --audio_type clean

# Day 3-4: Test with demixed audio
python compare_pipelines.py --audio_type demixed

# Day 5-7: Test with different quality levels
python compare_pipelines.py --audio_type compressed
```

### Phase 3: Advanced Improvements (Week 4-6) ⭐ **CRITICAL FOR PRODUCTION**

#### Week 4: Demucs Reprocessing & Retraining 🔥 **HIGHEST PRIORITY**

**This is THE most important improvement identified by the AnNOTEator team.**

```bash
# Day 1: Setup and prepare for Demucs processing
# Ensure you have enough disk space (200-300 GB)
df -h  # Check available space

# Install Demucs if not already installed
pip install demucs

# Test Demucs on a single file first
demucs --two-stems=drums test_audio.wav -o test_demucs_output/

# Day 2-4: Run full Demucs processing
# THIS IS EXTREMELY RESOURCE-INTENSIVE
# Estimated time: 20-40 hours on high-end workstation
# Run overnight and over weekend if needed

# Using Python script (recommended for better progress tracking)
python scripts/reprocess_training_with_demucs.py \
    --input AnNOTEator/dataset/e-gmd-v1.0.0/ \
    --output training_data/demucs_processed/ \
    --model htdemucs

# OR using bash script
bash scripts/reprocess_training_with_demucs.sh

# Monitor progress:
# - Check log files
# - Monitor disk space usage
# - Track processing speed (files per hour)

# Day 5-7: Retrain AnNOTEator with Demucs-processed data
# THIS IS ALSO VERY RESOURCE-INTENSIVE  
# Estimated time: 24-72 hours depending on GPU
# Requires good GPU (8GB+ VRAM recommended)

python AnNOTEator/model_development/train_model.py \
    --dataset training_data/demucs_processed/ \
    --model_name complete_network_demucs \
    --epochs 100 \
    --batch_size 32 \
    --learning_rate 0.001 \
    --validation_split 0.2 \
    --early_stopping_patience 10

# Monitor training:
# - Loss curves
# - Validation accuracy
# - Training time per epoch
# - GPU utilization (nvidia-smi -l 1)
```

**Expected Outcome**: 
- New model: `complete_network_demucs.h5`
- This model should perform SIGNIFICANTLY better on real-world Demucs-processed audio
- Essential for production GrooveSheet deployment

#### Week 5: Multi-Hit Improvements (AnNOTEator)
#### Week 5: Multi-Hit Improvements (AnNOTEator)
```bash
# Day 1-3: Generate synthetic multi-hit training data
python scripts/generate_multihit_training.py \
    --dataset AnNOTEator/dataset/e-gmd-v1.0.0/ \
    --output training_data/multihit/ \
    --threshold 0.05

# Day 4-7: Retrain model with multi-hit data
python AnNOTEator/model_development/train_model.py \
    --dataset training_data/multihit/ \
    --model_name complete_network_multihit \
    --epochs 100 \
    --batch_size 32
```

#### Week 6: Rhythm Correction (HMM) & Final Testing
```bash
# Day 1-3: Implement HMM rhythm correction
python scripts/train_rhythm_hmm.py \
    --dataset test_datasets/ground_truth/ \
    --output models/rhythm_hmm.pkl

# Day 4-5: Test HMM correction
python scripts/test_hmm_correction.py \
    --predictions results/annoteator/baseline/ \
    --hmm_model models/rhythm_hmm.pkl \
    --output results/annoteator/hmm_corrected/

# Day 6-7: Evaluate improvement
python scripts/evaluate_hmm_improvement.py
```

### Phase 4: Final Evaluation and Comparison (Week 7)

```bash
# Day 1-2: Run all improved models on full test dataset
python scripts/final_evaluation.py \
    --test_dataset test_datasets/ \
    --output results/final_evaluation/

# Day 3-4: Generate comparison reports
python scripts/generate_comparison_report.py \
    --results results/final_evaluation/ \
    --output reports/final_comparison.pdf

# Day 5-7: Analyze and document findings
python scripts/analyze_results.py \
    --results results/ \
    --output reports/analysis.md
```

---

## 7. Scripts to Create

### 7.1 Essential Testing Scripts

1. **`compare_pipelines.py`** - Main comparison script
2. **`evaluate_onset_detection.py`** - Onset metrics
3. **`evaluate_instrument_classification.py`** - Per-instrument accuracy
4. **`evaluate_rhythm_accuracy.py`** - Rhythm and timing metrics
5. **`analyze_midi.py`** - MIDI file analysis (you have this)
6. **`analyze_musicxml.py`** - MusicXML analysis
7. **`batch_processing.py`** - Process multiple files
8. **`generate_report.py`** - Create summary reports

### 7.2 Improvement Scripts

1. **`generate_multihit_training.py`** - Create multi-hit training data
2. **`batch_demucs_processing.py`** - Batch Demucs processing
3. **`train_rhythm_hmm.py`** - Train HMM for rhythm correction
4. **`test_augmentations.py`** - Test different augmentation configs
5. **`retrain_annoteator.py`** - Retrain with new data
6. **`apply_hmm_correction.py`** - Post-process with HMM

### 7.3 Analysis Scripts

1. **`visualize_results.py`** - Create charts and graphs
2. **`confusion_matrix.py`** - Instrument confusion analysis
3. **`timing_analysis.py`** - Onset timing distribution
4. **`error_analysis.py`** - Categorize and analyze errors

---

## 8. Expected Outcomes and Deliverables

### 8.1 Quantitative Results
- Precision, Recall, F1 scores for both pipelines
- Per-instrument accuracy breakdown
- Processing time comparisons
- Resource usage statistics

### 8.2 Qualitative Results
- MusicXML readability assessment
- Usability comparison
- Edge case handling

### 8.3 Recommendations
- Which pipeline works best for different scenarios:
  - Simple patterns vs complex patterns
  - Different genres
  - Clean vs demixed audio
  - Speed vs accuracy tradeoffs

### 8.4 Improved Models
- Retrained AnNOTEator models with:
  - Better multi-hit detection
  - Demucs-processed training data
  - Optimal augmentations
- Enhanced Omnizart configurations
- HMM rhythm correction models

---

## 9. Quick Start Checklist

For your friend at the science lab, here's a quick start checklist:

### Day 1: Setup
- [ ] Clone repository
- [ ] Install dependencies
- [ ] Verify GPU access (if available)
- [ ] Download test datasets

### Day 2-3: Baseline Testing
- [ ] Run both pipelines on test dataset
- [ ] Calculate baseline metrics
- [ ] Document baseline results

### Week 2-3: Comprehensive Testing
- [ ] Test different parameters
- [ ] Test different audio conditions
- [ ] Compare results

### Week 4-6: Improvements (Optional, Resource-Intensive)
- [ ] Retrain with multi-hit data
- [ ] Process with Demucs and retrain
- [ ] Implement HMM correction

### Week 7: Analysis and Reporting
- [ ] Generate final comparison
- [ ] Create visualizations
- [ ] Write recommendations

---

## 10. Contact and Support

For questions or issues during testing:
1. Check existing documentation in `ARCHITECTURE.md` and `QUICKSTART.md`
2. Review AnNOTEator's known issues (listed above)
3. Check Omnizart documentation: https://github.com/Music-and-Culture-Technology-Lab/omnizart

Good luck with your testing! This plan should give you a solid foundation for comprehensive evaluation and improvement of both pipelines.
