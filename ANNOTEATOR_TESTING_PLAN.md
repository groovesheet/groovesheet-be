# AnNOTEator Improvement & Testing Plan

## Overview
This document outlines a comprehensive strategy for improving and testing the AnNOTEator drum transcription pipeline.

**Focus**: Direct audio → MusicXML transcription using neural network-based drum detection.

---

## Table of Contents
1. [Known Issues & Recommendations](#known-issues--recommendations)
2. [Test Dataset Preparation](#test-dataset-preparation)
3. [Evaluation Metrics](#evaluation-metrics)
4. [Improvement Strategies](#improvement-strategies)
5. [Resource Requirements](#resource-requirements)
6. [Step-by-Step Execution Plan](#step-by-step-execution-plan)
7. [Scripts & Tools](#scripts--tools)

---

## 1. Known Issues & Recommendations

Based on the AnNOTEator team's documentation, here are the critical areas for improvement:

### Issue 1: Multi-Hit Label Underperformance 🔥 **HIGH PRIORITY**

**Problem:**
- The model underperforms on multi-hit label sound clips (simultaneous drums)
- ~80% of training data are single-labeled (one drum at a time)
- However, majority of real drum hits in songs are multi-hit
- Current implementation only merges hits if play-start time is within 0.02 seconds

**Impact:**
- Poor accuracy on realistic drum patterns
- Misses simultaneous kick+snare, hi-hat+kick combinations
- Most rock/pop songs have multi-hit patterns

**Recommendations:**
1. Increase the multi-hit threshold from 0.02s to 0.05s or higher
2. Generate synthetic multi-hit training data
3. Retrain with better multi-hit representation

---

### Issue 2: Quantization & Time Mapping Inaccuracy ⚠️ **MEDIUM PRIORITY**

**Problem:**
- Quantization algorithm is sensitive to exact timing
- Human performance has natural delays/variations
- Triplet notes misdetected as 16th notes due to slight delays
- Overall rhythm accuracy suffers

**Impact:**
- MusicXML has incorrect note durations
- Sheet music is harder to read
- Musicians can't use the transcription effectively

**Recommendations:**
1. Implement Hidden Markov Model (HMM) for rhythm correction
2. Use fuzzy/probabilistic quantization instead of hard thresholds
3. Consider musical context when determining note durations

---

### Issue 3: Demucs Processing Mismatch 🔥 **CRITICAL - HIGHEST PRIORITY**

**Problem:**
- Training data = clean, isolated drum recordings
- Production data = Demucs-processed audio (with filters, artifacts, alterations)
- Model sees very different audio characteristics in production vs training
- Demucs applies spectral filtering, phase changes, dynamic modifications

**Impact:**
- Significant accuracy drop on real-world Demucs-processed audio
- Model is essentially trained on the wrong domain
- This is THE most important issue to fix

**Recommendations:**
1. **Process entire E-GMD training dataset through Demucs**
2. Retrain AnNOTEator with Demucs-processed audio
3. This is resource-intensive but essential (20-40 hours processing time)

---

### Issue 4: Audio Augmentation Selection ⚠️ **MEDIUM PRIORITY**

**Problem:**
- Limited testing of optimal augmentations for demixed audio
- Time and resource limitations prevented extensive exploration
- Current augmentations may not represent production audio well

**Impact:**
- Model may not generalize well to varied audio conditions
- Suboptimal robustness to noise, compression, quality variations

**Recommendations:**
1. Systematic testing of Audiomentations library functions
2. Hyperparameter tuning for augmentation parameters
3. Build larger training dataset with augmentation variations

---

### Issue 5: Real-World Evaluation Dataset Missing 🔍 **LOW PRIORITY (BUT IMPORTANT)**

**Problem:**
- No existing dataset for evaluating pipeline on real-world music
- Difficult to measure production performance
- Can't benchmark against other systems effectively

**Impact:**
- Unknown real-world accuracy
- Hard to validate improvements
- No way to compare with competitors

**Recommendations:**
1. Create custom evaluation dataset with ground truth
2. Use professional drum recordings with manual annotations
3. Include variety of genres, tempos, complexities

---

### Issue 6: Notation Style Customization 📝 **LOW PRIORITY**

**Problem:**
- No standard style for drum sheet music
- Current implementation uses one specific style
- Changing style requires modifying transcriber.py code

**Impact:**
- May not match user preferences
- Limited flexibility for different use cases

**Recommendations:**
1. Create configurable notation styles
2. Allow users to choose between common conventions
3. Document how to customize (currently in transcriber script using Music21)

---

## 2. Test Dataset Preparation

### 2.1 E-GMD Dataset (Primary Training Data)
**Location:** `AnNOTEator/dataset/e-gmd-v1.0.0/`

**Contents:**
- Human-performed drum tracks
- MIDI ground truth available
- Multiple drummers and sessions
- Various genres and patterns

**Usage:**
1. Ground truth for evaluation
2. Training data augmentation
3. Demucs reprocessing source

### 2.2 Custom Test Sets to Create

#### Test Set 1: Multi-Hit Focus (20 samples)
- **Purpose:** Evaluate multi-hit detection
- **Patterns:**
  - Kick + Snare simultaneous
  - Hi-Hat + Kick combinations
  - Tom + Crash fills
  - Complex 3+ instrument hits
- **Tempos:** 80, 100, 120, 140 BPM
- **Time signature:** 4/4

#### Test Set 2: Rhythm Complexity (20 samples)
- **Purpose:** Test quantization accuracy
- **Patterns:**
  - Straight quarter/eighth/sixteenth notes
  - Triplets (eighth, sixteenth)
  - Syncopation
  - Shuffle patterns
  - Mixed note values
- **Tempos:** 60, 90, 120, 150, 180 BPM

#### Test Set 3: Real-World Songs (30 samples)
- **Purpose:** Production evaluation
- **Sources:**
  - Full songs processed with Demucs
  - Various genres (rock, pop, jazz, metal, funk)
  - Commercial recordings
  - Different audio qualities (studio, live, demo)

#### Test Set 4: Edge Cases (10 samples)
- **Purpose:** Robustness testing
- **Cases:**
  - Very fast tempos (>180 BPM)
  - Very slow tempos (<60 BPM)
  - Odd time signatures (7/8, 5/4, 3/4)
  - Extended technique (brushes, mallets)
  - Sparse vs dense patterns

### 2.3 Directory Structure

```bash
test_datasets/
├── e-gmd/                    # Original E-GMD dataset
├── e-gmd-demucs/            # Demucs-processed E-GMD
├── ground_truth/            # Reference MIDI files
├── multi_hit/               # Test Set 1
├── rhythm_complexity/       # Test Set 2
├── real_world/              # Test Set 3
├── edge_cases/              # Test Set 4
└── results/
    ├── baseline/            # Current model results
    ├── multihit_improved/   # After multi-hit improvements
    ├── demucs_retrained/    # After Demucs retraining
    └── hmm_corrected/       # After HMM rhythm correction
```

---

## 3. Evaluation Metrics

### 3.1 Onset Detection Accuracy

**Metrics:**
- **Precision**: TP / (TP + FP) - How many detected hits were correct?
- **Recall**: TP / (TP + FN) - How many actual hits were detected?
- **F1-Score**: Harmonic mean of precision and recall

**Tolerance Levels:**
- Strict: ±25ms
- Moderate: ±50ms
- Loose: ±100ms

**Per-Instrument Breakdown:**
- Kick/Bass Drum
- Snare Drum
- Hi-Hat (closed/open combined)
- Toms (all combined)
- Ride Cymbal
- Crash Cymbal

### 3.2 Multi-Hit Detection Rate

**Definition:** Percentage of correctly detected simultaneous drum hits

**Calculation:**
```
Multi-Hit Accuracy = (Correctly detected multi-hits) / (Total multi-hits in ground truth)
```

**Categories:**
- 2-instrument combinations (kick+snare, hihat+kick, etc.)
- 3+ instrument combinations
- Overall multi-hit accuracy

### 3.3 Rhythm Quantization Accuracy

**Metrics:**
- **Note Duration Accuracy**: % of notes with correct duration
- **Triplet Detection Rate**: Correctly identified triplets
- **Syncopation Accuracy**: Correctly placed off-beat notes
- **Timing Drift**: Accumulated error over time

**Measurement:**
Compare generated MusicXML note durations against ground truth MIDI

### 3.4 MusicXML Quality Assessment

**Automated Metrics:**
- Note density (notes per measure)
- Rest placement appropriateness
- Measure organization
- Tempo consistency

**Manual Assessment (Subjective):**
- Readability score (1-5)
- Playability by musician
- Correctness of notation symbols
- Overall usability

### 3.5 Performance Metrics

**Processing Speed:**
- Time per minute of audio
- Total processing time for dataset

**Resource Usage:**
- Peak RAM consumption
- GPU memory (if applicable)
- Disk I/O

---

## 4. Improvement Strategies

### 4.1 Multi-Hit Label Generation ⭐ **Priority 1**

#### Approach 1: Increase Threshold

**Current:** Merges hits within 0.02s (20ms)

**Test thresholds:**
- 0.03s (30ms)
- 0.05s (50ms)
- 0.08s (80ms)
- 0.10s (100ms)

**Implementation:**
```python
# Modify AnNOTEator/model_development/data_preparation.py

MULTI_HIT_THRESHOLD = 0.05  # Increase from 0.02

def merge_simultaneous_hits(hit_list, threshold=MULTI_HIT_THRESHOLD):
    """
    Merge drum hits that occur within threshold window
    """
    # Implementation here
    pass
```

**Evaluation:**
- Generate training data with each threshold
- Count multi-hit vs single-hit samples
- Train small model on each
- Evaluate multi-hit detection accuracy

#### Approach 2: Synthetic Multi-Hit Generation

**Strategy:** Combine single-hit samples to create realistic multi-hits

**Implementation:**
```python
# Script: scripts/generate_synthetic_multihit.py

import numpy as np
import librosa
import soundfile as sf

def create_multihit_sample(samples_dict, combination=['KD', 'SD']):
    """
    Mix multiple single-hit samples to create multi-hit training data
    
    Args:
        samples_dict: Dict of single-hit samples by instrument
        combination: List of instruments to combine
    
    Returns:
        Mixed audio array with multi-hit label
    """
    # Load single-hit samples
    mixed = np.zeros_like(samples_dict[combination[0]])
    
    for inst in combination:
        # Add slight time variation (0-5ms) for realism
        delay = np.random.randint(0, int(0.005 * sr))  # 0-5ms
        sample = samples_dict[inst]
        
        # Apply random gain variation (0.8-1.2)
        gain = np.random.uniform(0.8, 1.2)
        sample = sample * gain
        
        # Pad and add
        if delay > 0:
            sample = np.pad(sample, (delay, 0), mode='constant')[:len(mixed)]
        
        mixed += sample
    
    # Normalize
    mixed = mixed / np.max(np.abs(mixed)) * 0.9
    
    return mixed

# Common combinations to generate
combinations = [
    ['KD', 'SD'],           # Kick + Snare (very common)
    ['KD', 'HH'],           # Kick + Hi-Hat (very common)
    ['SD', 'HH'],           # Snare + Hi-Hat (common)
    ['KD', 'SD', 'HH'],     # Full beat (common)
    ['SD', 'TT'],           # Snare + Tom (fills)
    ['TT', 'CC'],           # Tom + Crash (fills)
    ['KD', 'RC'],           # Kick + Ride (jazz)
    ['SD', 'RC'],           # Snare + Ride (jazz)
]

# Generate 1000 samples per combination
for combo in combinations:
    for i in range(1000):
        sample = create_multihit_sample(single_hit_samples, combo)
        save_sample(sample, combo, i)
```

**Expected Results:**
- 8,000+ synthetic multi-hit samples
- Balanced dataset (~50% multi-hit, ~50% single-hit)
- Improved multi-hit detection accuracy

#### Approach 3: Data Augmentation During Training

**Strategy:** Apply augmentations that simulate multi-hit scenarios

```python
from audiomentations import Compose, TimeStretch, AddBackgroundNoise

augmenter = Compose([
    # Simulate drum bleed (other drums in background)
    AddBackgroundNoise(sounds_path="single_hit_samples/", p=0.3),
    
    # Slight timing variations
    TimeStretch(min_rate=0.98, max_rate=1.02, p=0.3),
])
```

---

### 4.2 Demucs Retraining 🔥 **Priority 1 - CRITICAL**

This is THE most important improvement. Production uses Demucs-processed audio, so training data MUST match.

#### Step 1: Process E-GMD with Demucs

**Script:** `reprocess_training_with_demucs.py` (already created)

**Command:**
```bash
python reprocess_training_with_demucs.py \
    --input AnNOTEator/dataset/e-gmd-v1.0.0/ \
    --output training_data/demucs_processed/ \
    --model htdemucs \
    --format mp3
```

**Parameters:**
- Model: `htdemucs` (best quality/speed balance)
- Format: MP3 (320kbps to save space, or use FLAC for lossless)
- Time: ~20-40 hours on high-end workstation
- Storage: ~200-300 GB

#### Step 2: Analyze Demucs Effects

Before retraining, understand what Demucs does:

**Script:** `scripts/analyze_demucs_effects.py` (already documented in plan)

**Analysis:**
- Frequency response changes
- Spectral centroid shift
- Dynamic range compression
- Harmonic vs percussive content
- Artifacts and noise

**Command:**
```bash
python scripts/analyze_demucs_effects.py \
    --original e-gmd/drummer1/session1/sample1.wav \
    --processed demucs_processed/drummer1/session1/sample1_drums.mp3 \
    --output-json demucs_analysis.json \
    --output-plot demucs_comparison.png
```

#### Step 3: Retrain AnNOTEator

**Command:**
```bash
python AnNOTEator/model_development/train_model.py \
    --dataset training_data/demucs_processed/ \
    --model_name complete_network_demucs \
    --epochs 100 \
    --batch_size 32 \
    --learning_rate 0.001 \
    --validation_split 0.2 \
    --early_stopping_patience 10 \
    --save_best_only
```

**Training Parameters:**
- Epochs: 100 (with early stopping)
- Batch size: 32 (adjust based on GPU memory)
- Learning rate: 0.001 (Adam optimizer)
- Validation: 20% of data
- Time: 24-72 hours depending on GPU

**Expected Results:**
- New model: `complete_network_demucs.h5`
- Significantly better accuracy on Demucs-processed audio
- Essential for production deployment

---

### 4.3 Hidden Markov Model (HMM) for Rhythm Correction ⭐ **Priority 2**

#### Concept

Use HMM to correct quantization errors based on:
- Musical context (previous notes)
- Tempo consistency
- Common rhythmic patterns
- Genre conventions

#### Implementation

**Script:** `scripts/train_rhythm_hmm.py`

```python
from hmmlearn import hmm
import numpy as np

class RhythmHMM:
    """
    Hidden Markov Model for rhythm correction
    
    States represent note durations:
    - Quarter note (1.0)
    - Eighth note (0.5)
    - Sixteenth note (0.25)
    - Eighth triplet (0.333)
    - Sixteenth triplet (0.167)
    """
    
    def __init__(self, n_states=5):
        self.n_states = n_states
        self.model = hmm.GaussianHMM(n_components=n_states, covariance_type="diag")
        
        # State labels
        self.states = {
            0: 1.0,      # Quarter
            1: 0.5,      # Eighth
            2: 0.25,     # Sixteenth
            3: 0.333,    # Eighth triplet
            4: 0.167,    # Sixteenth triplet
        }
    
    def train(self, correct_sequences):
        """
        Train HMM on known-correct rhythm sequences
        
        Args:
            correct_sequences: List of (duration_values, tempo) tuples
        """
        X = []
        lengths = []
        
        for seq, tempo in correct_sequences:
            # Convert durations to features
            features = self.extract_features(seq, tempo)
            X.extend(features)
            lengths.append(len(features))
        
        X = np.array(X).reshape(-1, 1)
        
        # Train model
        self.model.fit(X, lengths)
    
    def extract_features(self, durations, tempo):
        """Extract features from note durations"""
        # Normalize by tempo
        qn_per_sec = tempo / 60.0
        normalized = [d * qn_per_sec for d in durations]
        return normalized
    
    def correct_rhythm(self, predicted_durations, tempo):
        """
        Apply HMM to correct predicted note durations
        
        Args:
            predicted_durations: List of raw predicted durations
            tempo: Detected tempo (BPM)
        
        Returns:
            Corrected durations
        """
        # Extract features
        features = self.extract_features(predicted_durations, tempo)
        X = np.array(features).reshape(-1, 1)
        
        # Predict most likely state sequence
        states = self.model.predict(X)
        
        # Map states to durations
        corrected = [self.states[s] for s in states]
        
        return corrected

# Training
hmm_model = RhythmHMM(n_states=5)

# Load ground truth sequences
correct_sequences = load_ground_truth_sequences("test_datasets/ground_truth/")

# Train
hmm_model.train(correct_sequences)

# Save model
import pickle
with open('models/rhythm_hmm.pkl', 'wb') as f:
    pickle.dump(hmm_model, f)
```

#### Integration with AnNOTEator

**Modify:** `AnNOTEator/inference/transcriber.py`

```python
# Add HMM correction step in sheet_construction method

def sheet_construction(self, music21_data, song_title=None, use_hmm=True):
    """
    Construct sheet music with optional HMM rhythm correction
    """
    if use_hmm and os.path.exists('models/rhythm_hmm.pkl'):
        # Load HMM model
        with open('models/rhythm_hmm.pkl', 'rb') as f:
            hmm_model = pickle.load(f)
        
        # Extract durations from music21_data
        durations = [note[0] for measure in music21_data for note in measure]
        
        # Correct with HMM
        corrected_durations = hmm_model.correct_rhythm(durations, self.bpm)
        
        # Update music21_data with corrected durations
        # (implementation details)
    
    # Continue with normal sheet construction
    # ...
```

**Expected Results:**
- 10-20% improvement in rhythm accuracy
- Fewer quantization errors
- More musically sensible note durations

---

### 4.4 Audio Augmentation Optimization ⭐ **Priority 2**

#### Systematic Testing Approach

**Goal:** Find optimal augmentation parameters for Demucs-processed audio

**Strategy:** Grid search over augmentation combinations

#### Augmentation Library

```python
from audiomentations import (
    Compose, AddGaussianNoise, TimeStretch, PitchShift,
    Shift, Gain, BandPassFilter, LowPassFilter, HighPassFilter,
    Mp3Compression, Limiter, Normalize
)
```

#### Test Configurations

**Config 1: Conservative (Baseline)**
```python
augment_conservative = Compose([
    AddGaussianNoise(min_amplitude=0.001, max_amplitude=0.005, p=0.3),
    Gain(min_gain_in_db=-3, max_gain_in_db=3, p=0.5),
])
```

**Config 2: Moderate**
```python
augment_moderate = Compose([
    AddGaussianNoise(min_amplitude=0.001, max_amplitude=0.01, p=0.5),
    TimeStretch(min_rate=0.95, max_rate=1.05, p=0.3),
    Gain(min_gain_in_db=-6, max_gain_in_db=6, p=0.5),
    BandPassFilter(min_center_freq=80, max_center_freq=8000, p=0.2),
])
```

**Config 3: Aggressive**
```python
augment_aggressive = Compose([
    AddGaussianNoise(min_amplitude=0.001, max_amplitude=0.015, p=0.5),
    TimeStretch(min_rate=0.9, max_rate=1.1, p=0.5),
    PitchShift(min_semitones=-1, max_semitones=1, p=0.3),
    Gain(min_gain_in_db=-9, max_gain_in_db=9, p=0.5),
    BandPassFilter(min_center_freq=80, max_center_freq=8000, p=0.3),
    Mp3Compression(min_bitrate=128, max_bitrate=320, p=0.3),
])
```

**Config 4: Demucs-Specific**
```python
augment_demucs_specific = Compose([
    # Simulate Demucs artifacts
    AddGaussianNoise(min_amplitude=0.002, max_amplitude=0.008, p=0.6),
    
    # Simulate spectral filtering
    BandPassFilter(min_center_freq=40, max_center_freq=16000, p=0.4),
    
    # Simulate compression/limiting
    Limiter(min_threshold_db=-12, max_threshold_db=-3, p=0.5),
    
    # Gain variations
    Gain(min_gain_in_db=-4, max_gain_in_db=4, p=0.6),
])
```

#### Evaluation Script

```python
# Script: scripts/test_augmentation_configs.py

configs = {
    'conservative': augment_conservative,
    'moderate': augment_moderate,
    'aggressive': augment_aggressive,
    'demucs_specific': augment_demucs_specific,
}

results = {}

for config_name, augmenter in configs.items():
    print(f"Testing {config_name} configuration...")
    
    # Train model with this augmentation
    model = train_with_augmentation(
        dataset='training_data/demucs_processed/',
        augmenter=augmenter,
        model_name=f'complete_network_{config_name}',
        epochs=50  # Fewer epochs for testing
    )
    
    # Evaluate on test set
    metrics = evaluate_model(
        model=model,
        test_dataset='test_datasets/real_world/',
        ground_truth='test_datasets/ground_truth/'
    )
    
    results[config_name] = metrics
    
    print(f"  F1-Score: {metrics['f1_score']:.4f}")
    print(f"  Multi-hit accuracy: {metrics['multihit_accuracy']:.4f}")
    print(f"  Rhythm accuracy: {metrics['rhythm_accuracy']:.4f}")

# Save results
with open('results/augmentation_comparison.json', 'w') as f:
    json.dump(results, f, indent=2)

# Select best configuration
best_config = max(results.items(), key=lambda x: x[1]['f1_score'])
print(f"\nBest configuration: {best_config[0]}")
```

---

### 4.5 Build Larger Training Dataset ⭐ **Priority 3**

#### Strategy

Combine multiple data sources with extensive augmentation

#### Data Sources

1. **E-GMD (Primary)**: ~1,200 drum recordings
2. **ENST-Drums**: ~200 professional recordings
3. **Custom recordings**: 100+ samples (if possible)
4. **Synthetic multi-hits**: 8,000+ generated samples

#### Augmentation Pipeline

```python
# Generate 10x more training data through augmentation

# For each original sample, create:
# - 1 original
# - 3 with different noise levels
# - 2 with time stretching
# - 2 with EQ changes
# - 2 with gain variations
# Total: 10 samples per original

def augment_dataset(input_dir, output_dir, multiplier=10):
    """
    Augment entire dataset with variations
    """
    samples = load_samples(input_dir)
    
    for sample in samples:
        # Save original
        save_sample(sample, output_dir, f"{sample.id}_00_original")
        
        # Generate variations
        for i in range(1, multiplier):
            # Randomly select augmentation
            aug = random.choice([
                augment_noise,
                augment_time_stretch,
                augment_eq,
                augment_gain,
                augment_combined
            ])
            
            augmented = aug(sample)
            save_sample(augmented, output_dir, f"{sample.id}_{i:02d}_aug")
```

**Expected Result:**
- Training dataset: 12,000+ → 120,000+ samples
- Better generalization
- Improved robustness

---

## 5. Resource Requirements

### 5.1 Hardware Requirements

#### Minimum (Testing Only):
- CPU: 4+ cores
- RAM: 16 GB
- Storage: 100 GB
- GPU: Not required (but slower)
- Time: Can do basic testing

#### Recommended (Full Testing):
- CPU: 8+ cores
- RAM: 32 GB
- Storage: 250 GB
- GPU: 6+ GB VRAM (optional, speeds up training)
- Time: Complete evaluation in reasonable time

#### Optimal (All Improvements):
- CPU: 16+ cores (for Demucs processing)
- RAM: 64 GB
- Storage: 500 GB - 1 TB
- GPU: 8+ GB VRAM (NVIDIA for CUDA support)
- Time: Complete all improvements including retraining

### 5.2 Storage Breakdown

```
E-GMD original:              ~50 GB
E-GMD Demucs-processed:      ~200 GB
Synthetic multi-hit data:    ~30 GB
Augmented dataset:           ~100 GB
Model checkpoints:           ~20 GB
Test results:                ~10 GB
Backup/intermediate:         ~90 GB
---
Total:                       ~500 GB
```

### 5.3 Time Estimates

**Phase 1: Demucs Processing**
- Time: 20-40 hours (depends on CPU)
- Can run overnight/weekend

**Phase 2: Retraining**
- Time: 24-72 hours per model
- Depends on GPU availability

**Phase 3: Evaluation**
- Time: 4-8 hours
- Run on all test sets

**Phase 4: HMM & Augmentation**
- Time: 16-24 hours
- Additional iterations

**Total: 5-8 weeks** (including experiments and iterations)

---

## 6. Step-by-Step Execution Plan

### Week 1: Setup & Baseline

#### Day 1-2: Environment Setup
```bash
# 1. Setup workspace
cd /path/to/drumscore-be

# 2. Verify AnNOTEator installation
python -c "from AnNOTEator.inference import predict_drumhit; print('OK')"

# 3. Install additional dependencies
pip install hmmlearn audiomentations tqdm matplotlib seaborn

# 4. Create directory structure
mkdir -p test_datasets/{ground_truth,multi_hit,rhythm_complexity,real_world,edge_cases}
mkdir -p test_datasets/results/{baseline,multihit_improved,demucs_retrained,hmm_corrected}
mkdir -p training_data/{demucs_processed,synthetic_multihit,augmented}
mkdir -p models
mkdir -p scripts
```

#### Day 3-4: Test Dataset Preparation
```bash
# 1. Organize E-GMD dataset
python scripts/organize_test_dataset.py

# 2. Create ground truth MIDI files
# (Manual or use existing E-GMD MIDI)

# 3. Generate audio from MIDI (if needed)
python scripts/midi_to_audio.py \
    --input test_datasets/ground_truth/ \
    --output test_datasets/audio_generated/
```

#### Day 5-7: Baseline Testing
```bash
# 1. Run AnNOTEator baseline on test sets
python annoteator_convert_baseline_wav_to_musicxml.py \
    --input test_datasets/multi_hit/ \
    --output test_datasets/results/baseline/multi_hit/

python annoteator_convert_baseline_wav_to_musicxml.py \
    --input test_datasets/rhythm_complexity/ \
    --output test_datasets/results/baseline/rhythm_complexity/

python annoteator_convert_baseline_wav_to_musicxml.py \
    --input test_datasets/real_world/ \
    --output test_datasets/results/baseline/real_world/

# 2. Evaluate baseline performance
python scripts/evaluate_baseline.py \
    --ground_truth test_datasets/ground_truth/ \
    --predictions test_datasets/results/baseline/ \
    --output results/baseline_metrics.json

# 3. Document baseline performance
# Record F1-scores, multi-hit accuracy, rhythm accuracy
```

**Baseline Metrics to Record:**
- Overall F1-score
- Per-instrument accuracy
- Multi-hit detection rate
- Rhythm quantization accuracy
- Processing time

---

### Week 2-3: Multi-Hit Improvements

#### Week 2: Threshold Testing & Synthetic Generation

**Day 1-2: Test Different Thresholds**
```bash
# Test multiple threshold values
for threshold in 0.03 0.05 0.08 0.10; do
    python scripts/regenerate_training_with_threshold.py \
        --input AnNOTEator/dataset/e-gmd-v1.0.0/ \
        --output training_data/threshold_$threshold/ \
        --threshold $threshold
    
    # Count multi-hit vs single-hit samples
    python scripts/count_multihit_samples.py \
        --dataset training_data/threshold_$threshold/ \
        --output results/threshold_${threshold}_stats.json
done
```

**Day 3-5: Generate Synthetic Multi-Hit Data**
```bash
# Create synthetic multi-hit training samples
python scripts/generate_synthetic_multihit.py \
    --single_hits AnNOTEator/dataset/e-gmd-v1.0.0/ \
    --output training_data/synthetic_multihit/ \
    --samples_per_combo 1000 \
    --combinations "KD,SD" "KD,HH" "SD,HH" "KD,SD,HH" "SD,TT" "TT,CC"

# Expected output: ~8,000 synthetic multi-hit samples
```

**Day 6-7: Retrain with Best Threshold**
```bash
# Select best threshold based on sample distribution
# Assume 0.05s was best

# Retrain model
python AnNOTEator/model_development/train_model.py \
    --dataset training_data/threshold_0.05/ \
    --model_name complete_network_multihit_05 \
    --epochs 100 \
    --batch_size 32
```

#### Week 3: Evaluation & Refinement

**Day 1-3: Test Multi-Hit Improved Model**
```bash
# Run improved model on test sets
python scripts/test_improved_model.py \
    --model models/complete_network_multihit_05.h5 \
    --input test_datasets/multi_hit/ \
    --output test_datasets/results/multihit_improved/

# Evaluate
python evaluate_onset_detection.py \
    --ground-truth test_datasets/ground_truth/ \
    --predicted test_datasets/results/multihit_improved/ \
    --output results/multihit_improved_metrics.json
```

**Day 4-5: Compare with Baseline**
```bash
# Generate comparison report
python scripts/compare_models.py \
    --baseline results/baseline_metrics.json \
    --improved results/multihit_improved_metrics.json \
    --output reports/multihit_improvement.html
```

**Day 6-7: Fine-tune & Iterate**
- Adjust if needed
- Try combining threshold + synthetic data
- Document results

---

### Week 4: Demucs Retraining 🔥 **CRITICAL WEEK**

This is THE most important improvement.

#### Day 1: Prepare for Demucs Processing

```bash
# 1. Check disk space (need 250+ GB)
df -h

# 2. Test Demucs on single file
demucs --two-stems=drums test_sample.wav -o test_demucs_output/

# 3. Verify output quality
python scripts/analyze_demucs_effects.py \
    --original test_sample.wav \
    --processed test_demucs_output/htdemucs/test_sample/drums.mp3

# 4. Create processing script if needed
```

#### Day 2-4: Run Full Demucs Processing ⏰

**THIS IS VERY RESOURCE-INTENSIVE - RUN OVERNIGHT/WEEKEND**

```bash
# Process entire E-GMD dataset
python reprocess_training_with_demucs.py \
    --input AnNOTEator/dataset/e-gmd-v1.0.0/ \
    --output training_data/demucs_processed/ \
    --model htdemucs \
    --format mp3

# Monitor progress:
# - Check processing_stats.json periodically
# - Estimate: 20-40 hours on high-end workstation
# - ~1200 files × 1-2 minutes per file

# Run in background (Linux/Mac):
nohup python reprocess_training_with_demucs.py \
    --input AnNOTEator/dataset/e-gmd-v1.0.0/ \
    --output training_data/demucs_processed/ \
    --model htdemucs \
    --format mp3 > demucs_processing.log 2>&1 &

# Or use tmux/screen to prevent disconnection
```

**Monitor Progress:**
```bash
# Check log
tail -f demucs_processing.log

# Check stats
cat training_data/demucs_processed/processing_stats.json | grep successful
```

#### Day 5-7: Retrain with Demucs Data

**THIS IS ALSO VERY RESOURCE-INTENSIVE**

```bash
# Retrain AnNOTEator with Demucs-processed audio
python AnNOTEator/model_development/train_model.py \
    --dataset training_data/demucs_processed/ \
    --model_name complete_network_demucs \
    --epochs 100 \
    --batch_size 32 \
    --learning_rate 0.001 \
    --validation_split 0.2 \
    --early_stopping_patience 10 \
    --save_best_only

# Expected time: 24-72 hours depending on GPU
# Monitor training:
# - Loss curves
# - Validation accuracy
# - GPU utilization (nvidia-smi -l 1)
```

**Training Tips:**
- Use GPU if available
- Monitor for overfitting
- Save checkpoints regularly
- Can reduce epochs if time-constrained

---

### Week 5: HMM Rhythm Correction

#### Day 1-3: Implement & Train HMM

```bash
# 1. Create HMM training script
# (Use implementation from Section 4.3)

# 2. Prepare ground truth sequences
python scripts/extract_ground_truth_sequences.py \
    --midi_dir test_datasets/ground_truth/ \
    --output training_data/hmm_sequences.pkl

# 3. Train HMM model
python scripts/train_rhythm_hmm.py \
    --sequences training_data/hmm_sequences.pkl \
    --output models/rhythm_hmm.pkl \
    --n_states 5

# 4. Integrate with AnNOTEator transcriber
# Modify AnNOTEator/inference/transcriber.py
# Add HMM correction option
```

#### Day 4-7: Test & Evaluate HMM

```bash
# 1. Test HMM correction on baseline results
python scripts/apply_hmm_correction.py \
    --predictions test_datasets/results/baseline/ \
    --hmm_model models/rhythm_hmm.pkl \
    --output test_datasets/results/hmm_corrected/

# 2. Evaluate rhythm accuracy
python scripts/evaluate_rhythm_accuracy.py \
    --ground_truth test_datasets/ground_truth/ \
    --predictions test_datasets/results/hmm_corrected/ \
    --output results/hmm_metrics.json

# 3. Compare with baseline
python scripts/compare_rhythm_accuracy.py \
    --baseline results/baseline_metrics.json \
    --hmm_corrected results/hmm_metrics.json \
    --output reports/hmm_improvement.html
```

---

### Week 6: Augmentation Optimization

#### Day 1-3: Test Augmentation Configs

```bash
# Run systematic augmentation testing
python scripts/test_augmentation_configs.py \
    --dataset training_data/demucs_processed/ \
    --configs conservative moderate aggressive demucs_specific \
    --epochs 50 \
    --output results/augmentation_comparison.json
```

#### Day 4-5: Train with Best Config

```bash
# Select best augmentation configuration
python scripts/select_best_augmentation.py \
    --comparison results/augmentation_comparison.json \
    --output best_augmentation_config.json

# Retrain with optimal augmentation
python AnNOTEator/model_development/train_model.py \
    --dataset training_data/demucs_processed/ \
    --augmentation_config best_augmentation_config.json \
    --model_name complete_network_demucs_augmented \
    --epochs 100
```

#### Day 6-7: Build Larger Dataset

```bash
# Apply augmentation to create larger dataset
python scripts/augment_dataset.py \
    --input training_data/demucs_processed/ \
    --output training_data/augmented/ \
    --config best_augmentation_config.json \
    --multiplier 5

# This creates 5x more training data
```

---

### Week 7: Final Evaluation & Comparison

#### Day 1-2: Test All Improved Models

```bash
# Test each improved model on full test suite
models=(
    "models/complete_network_multihit_05.h5"
    "models/complete_network_demucs.h5"
    "models/complete_network_demucs_augmented.h5"
)

for model in "${models[@]}"; do
    model_name=$(basename $model .h5)
    
    python scripts/full_evaluation.py \
        --model $model \
        --test_datasets test_datasets/ \
        --ground_truth test_datasets/ground_truth/ \
        --output results/${model_name}_evaluation.json \
        --apply_hmm models/rhythm_hmm.pkl
done
```

#### Day 3-4: Generate Comprehensive Report

```bash
# Create final comparison report
python scripts/generate_final_report.py \
    --baseline results/baseline_metrics.json \
    --multihit results/complete_network_multihit_05_evaluation.json \
    --demucs results/complete_network_demucs_evaluation.json \
    --demucs_aug results/complete_network_demucs_augmented_evaluation.json \
    --output reports/final_comparison.html

# Generate visualizations
python scripts/visualize_improvements.py \
    --results results/ \
    --output reports/visualizations/
```

#### Day 5-7: Documentation & Deployment

```bash
# 1. Document all improvements
# - Write summary of what worked
# - Record metrics improvements
# - Note any failures/learnings

# 2. Select best model for production
python scripts/select_production_model.py \
    --evaluations results/ \
    --output production_model_recommendation.json

# 3. Update production configuration
# Copy best model to production location
cp models/complete_network_demucs_augmented.h5 \
   backend/models/annoteator_production.h5

# 4. Update backend to use new model
# Modify backend configuration

# 5. Create deployment documentation
# - Model specifications
# - Performance metrics
# - Known limitations
# - Recommended settings
```

---

## 7. Scripts & Tools

### 7.1 Evaluation Scripts

**Already Created:**
- `evaluate_onset_detection.py` - Calculate precision, recall, F1-score
- `compare_pipelines.py` - Compare model outputs (needs modification to remove Omnizart)
- `annoteator_convert_baseline_wav_to_musicxml.py` - Run AnNOTEator

**Need to Create:**

1. **`scripts/evaluate_multihit_detection.py`**
   - Calculate multi-hit detection rate
   - Per-combination accuracy
   - Confusion matrix for instrument combinations

2. **`scripts/evaluate_rhythm_accuracy.py`**
   - Note duration accuracy
   - Triplet detection rate
   - Timing drift measurement

3. **`scripts/compare_models.py`**
   - Side-by-side model comparison
   - Statistical significance testing
   - Visualization of improvements

4. **`scripts/generate_final_report.py`**
   - Comprehensive HTML report
   - Charts and graphs
   - Summary statistics

### 7.2 Data Processing Scripts

**Already Created:**
- `reprocess_training_with_demucs.py` - Process dataset with Demucs

**Need to Create:**

1. **`scripts/generate_synthetic_multihit.py`**
   - Combine single-hit samples
   - Generate realistic multi-hit training data
   - Apply timing variations and mixing

2. **`scripts/augment_dataset.py`**
   - Apply audiomentations
   - Create multiple variations
   - Expand training dataset

3. **`scripts/organize_test_dataset.py`**
   - Organize files into proper structure
   - Validate ground truth MIDI
   - Create dataset metadata

4. **`scripts/analyze_demucs_effects.py`**
   - Spectral analysis
   - Feature comparison
   - Visualization

### 7.3 Training Scripts

**Need to Create:**

1. **`scripts/train_with_augmentation.py`**
   - Wrapper for training with specific augmentation config
   - Cross-validation support
   - Hyperparameter logging

2. **`scripts/test_augmentation_configs.py`**
   - Grid search augmentation parameters
   - Train multiple models
   - Compare results

3. **`scripts/train_rhythm_hmm.py`**
   - Train HMM on ground truth sequences
   - Hyperparameter tuning
   - Save trained model

### 7.4 Integration Scripts

**Need to Create:**

1. **`scripts/apply_hmm_correction.py`**
   - Post-process AnNOTEator output
   - Apply HMM rhythm correction
   - Save corrected MusicXML

2. **`scripts/test_improved_model.py`**
   - Run improved model on test set
   - Generate predictions
   - Save results

---

## 8. Expected Outcomes

### 8.1 Performance Improvements

**Baseline (Current):**
- Overall F1-score: ~0.70-0.75
- Multi-hit accuracy: ~0.50-0.60
- Rhythm accuracy: ~0.65-0.70

**After Multi-Hit Improvements:**
- Overall F1-score: ~0.75-0.80 (+5-10%)
- Multi-hit accuracy: ~0.70-0.75 (+20-25%)
- Rhythm accuracy: ~0.65-0.70 (no change)

**After Demucs Retraining:** 🔥
- Overall F1-score: ~0.80-0.85 (+15-20%)
- Multi-hit accuracy: ~0.75-0.80 (+25-30%)
- Rhythm accuracy: ~0.70-0.75 (+5-10%)
- **This is the biggest improvement**

**After HMM Rhythm Correction:**
- Overall F1-score: ~0.80-0.85 (no change)
- Multi-hit accuracy: ~0.75-0.80 (no change)
- Rhythm accuracy: ~0.80-0.85 (+15-20%)

**After Augmentation Optimization:**
- Overall F1-score: ~0.85-0.90 (+5-10%)
- Multi-hit accuracy: ~0.80-0.85 (+5-10%)
- Rhythm accuracy: ~0.80-0.85 (no change)

**Final Combined Model:**
- Overall F1-score: **~0.85-0.90** (+20-30% from baseline)
- Multi-hit accuracy: **~0.80-0.85** (+40-50% from baseline)
- Rhythm accuracy: **~0.80-0.85** (+20-30% from baseline)

### 8.2 Production Readiness

**After Improvements:**
- ✅ Accurate on real-world Demucs-processed audio
- ✅ Good multi-hit detection for realistic drum patterns
- ✅ Improved rhythm quantization
- ✅ Robust to audio quality variations
- ✅ Ready for GrooveSheet production deployment

---

## 9. Priority Summary

### 🔥 **MUST DO (Critical for Production)**

1. **Demucs Retraining** - Week 4
   - Process E-GMD with Demucs
   - Retrain AnNOTEator
   - This is THE most important improvement

### ⭐ **SHOULD DO (Significant Improvements)**

2. **Multi-Hit Improvements** - Week 2-3
   - Increase threshold
   - Generate synthetic data
   - Improves realistic drum pattern accuracy

3. **HMM Rhythm Correction** - Week 5
   - Train HMM on ground truth
   - Integrate with transcriber
   - Significantly improves rhythm accuracy

4. **Augmentation Optimization** - Week 6
   - Test augmentation configs
   - Select best parameters
   - Improves generalization

### 🔍 **NICE TO HAVE (Polish & Refinement)**

5. **Real-World Evaluation Dataset** - Ongoing
   - Create comprehensive test set
   - Better production metrics

6. **Notation Style Customization** - Future
   - Configurable styles
   - User preferences

---

## 10. Success Criteria

### Minimum Success (Must Achieve):
- ✅ F1-score ≥ 0.80 on Demucs-processed audio
- ✅ Multi-hit accuracy ≥ 0.70
- ✅ Rhythm accuracy ≥ 0.75
- ✅ Model works on real-world songs

### Target Success (Should Achieve):
- ✅ F1-score ≥ 0.85
- ✅ Multi-hit accuracy ≥ 0.75
- ✅ Rhythm accuracy ≥ 0.80
- ✅ Processing time < 2 minutes per minute of audio

### Stretch Goals (Nice to Have):
- ✅ F1-score ≥ 0.90
- ✅ Multi-hit accuracy ≥ 0.85
- ✅ Rhythm accuracy ≥ 0.85
- ✅ Works well across all genres and tempos

---

## 11. Risk Mitigation

### Risk 1: Insufficient Resources
**Mitigation:**
- Start with most critical improvement (Demucs)
- Use cloud resources if needed
- Reduce dataset size for initial tests

### Risk 2: Longer Than Expected
**Mitigation:**
- Prioritize Demucs retraining
- Run processes overnight/weekend
- Parallelize where possible

### Risk 3: Improvements Don't Work
**Mitigation:**
- Document what doesn't work
- Try alternative approaches
- At minimum, get Demucs retraining done

---

**Good luck with improving AnNOTEator! Focus on Demucs retraining first - it's the most impactful change.** 🚀
