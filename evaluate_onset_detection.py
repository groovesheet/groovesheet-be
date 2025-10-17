"""
Onset Detection Evaluation
Compares predicted drum onsets against ground truth
Calculates Precision, Recall, F1-Score with different tolerance windows
"""

import os
import numpy as np
import pretty_midi
import json
from pathlib import Path

def extract_onsets_from_midi(midi_path, instrument_filter=None):
    """
    Extract onset times from MIDI file
    
    Args:
        midi_path: Path to MIDI file
        instrument_filter: Optional drum pitch filter (e.g., [36, 38, 42] for kick, snare, hihat)
    
    Returns:
        Dictionary with onset times per instrument
    """
    midi_data = pretty_midi.PrettyMIDI(midi_path)
    onsets = {}
    
    for instrument in midi_data.instruments:
        if not instrument.is_drum:
            continue
        
        for note in instrument.notes:
            pitch = note.pitch
            onset_time = note.start
            
            if instrument_filter is None or pitch in instrument_filter:
                if pitch not in onsets:
                    onsets[pitch] = []
                onsets[pitch].append(onset_time)
    
    # Sort all onset lists
    for pitch in onsets:
        onsets[pitch].sort()
    
    return onsets

def get_all_onsets(onset_dict):
    """
    Flatten onset dictionary to single list of all onsets
    """
    all_onsets = []
    for pitch, times in onset_dict.items():
        all_onsets.extend(times)
    return sorted(all_onsets)

def match_onsets(ground_truth_onsets, predicted_onsets, tolerance_sec=0.05):
    """
    Match predicted onsets to ground truth within tolerance window
    
    Args:
        ground_truth_onsets: List of ground truth onset times
        predicted_onsets: List of predicted onset times
        tolerance_sec: Tolerance window in seconds (default 50ms)
    
    Returns:
        Tuple of (true_positives, false_positives, false_negatives)
    """
    gt_onsets = np.array(sorted(ground_truth_onsets))
    pred_onsets = np.array(sorted(predicted_onsets))
    
    if len(gt_onsets) == 0:
        return 0, len(pred_onsets), 0
    
    if len(pred_onsets) == 0:
        return 0, 0, len(gt_onsets)
    
    # Track which ground truth onsets have been matched
    gt_matched = np.zeros(len(gt_onsets), dtype=bool)
    
    true_positives = 0
    false_positives = 0
    
    # For each predicted onset, find closest ground truth
    for pred_onset in pred_onsets:
        # Find closest ground truth onset
        distances = np.abs(gt_onsets - pred_onset)
        closest_idx = np.argmin(distances)
        closest_distance = distances[closest_idx]
        
        # Check if within tolerance and not already matched
        if closest_distance <= tolerance_sec and not gt_matched[closest_idx]:
            true_positives += 1
            gt_matched[closest_idx] = True
        else:
            false_positives += 1
    
    # Count unmatched ground truth onsets as false negatives
    false_negatives = np.sum(~gt_matched)
    
    return true_positives, false_positives, false_negatives

def calculate_metrics(tp, fp, fn):
    """
    Calculate precision, recall, and F1 score
    """
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'true_positives': int(tp),
        'false_positives': int(fp),
        'false_negatives': int(fn)
    }

def evaluate_onset_detection(ground_truth_midi, predicted_midi, tolerances_ms=[25, 50, 100]):
    """
    Evaluate onset detection accuracy at multiple tolerance levels
    
    Args:
        ground_truth_midi: Path to ground truth MIDI file
        predicted_midi: Path to predicted MIDI file
        tolerances_ms: List of tolerance windows in milliseconds
    
    Returns:
        Dictionary with metrics at each tolerance level
    """
    print(f"\n{'='*70}")
    print(f"  Onset Detection Evaluation")
    print(f"{'='*70}")
    print(f"\nGround truth: {os.path.basename(ground_truth_midi)}")
    print(f"Predicted:    {os.path.basename(predicted_midi)}")
    
    # Extract onsets
    print("\n⏳ Extracting onsets...")
    gt_onsets_dict = extract_onsets_from_midi(ground_truth_midi)
    pred_onsets_dict = extract_onsets_from_midi(predicted_midi)
    
    gt_onsets = get_all_onsets(gt_onsets_dict)
    pred_onsets = get_all_onsets(pred_onsets_dict)
    
    print(f"✓ Ground truth: {len(gt_onsets)} onsets")
    print(f"✓ Predicted:    {len(pred_onsets)} onsets")
    
    # Calculate metrics at different tolerance levels
    results = {
        'ground_truth_file': ground_truth_midi,
        'predicted_file': predicted_midi,
        'ground_truth_count': len(gt_onsets),
        'predicted_count': len(pred_onsets),
        'tolerance_levels': {}
    }
    
    print(f"\n{'='*70}")
    print(f"  Metrics at Different Tolerance Levels")
    print(f"{'='*70}")
    
    for tolerance_ms in tolerances_ms:
        tolerance_sec = tolerance_ms / 1000.0
        
        tp, fp, fn = match_onsets(gt_onsets, pred_onsets, tolerance_sec)
        metrics = calculate_metrics(tp, fp, fn)
        
        results['tolerance_levels'][f'{tolerance_ms}ms'] = {
            'tolerance_sec': tolerance_sec,
            **metrics
        }
        
        print(f"\n  Tolerance: ±{tolerance_ms}ms")
        print(f"    Precision: {metrics['precision']:.4f} ({metrics['true_positives']}/{metrics['true_positives']+metrics['false_positives']})")
        print(f"    Recall:    {metrics['recall']:.4f} ({metrics['true_positives']}/{metrics['true_positives']+metrics['false_negatives']})")
        print(f"    F1-Score:  {metrics['f1_score']:.4f}")
    
    # Per-instrument evaluation (optional, if needed)
    print(f"\n{'='*70}")
    print(f"  Per-Instrument Breakdown")
    print(f"{'='*70}")
    
    # Common drum MIDI pitches
    drum_map = {
        35: 'Kick (Acoustic)',
        36: 'Kick (Bass Drum 1)',
        38: 'Snare',
        40: 'Snare (Electric)',
        42: 'Hi-Hat (Closed)',
        44: 'Hi-Hat (Pedal)',
        46: 'Hi-Hat (Open)',
        41: 'Floor Tom (Low)',
        43: 'Floor Tom (High)',
        45: 'Tom (Low)',
        47: 'Tom (Mid)',
        48: 'Tom (High)',
        50: 'Tom (High)',
        49: 'Crash 1',
        51: 'Ride',
        53: 'Ride (Bell)',
        55: 'Splash',
        57: 'Crash 2',
    }
    
    per_instrument_results = {}
    
    for pitch in sorted(set(gt_onsets_dict.keys()) | set(pred_onsets_dict.keys())):
        gt_inst_onsets = gt_onsets_dict.get(pitch, [])
        pred_inst_onsets = pred_onsets_dict.get(pitch, [])
        
        if len(gt_inst_onsets) > 0 or len(pred_inst_onsets) > 0:
            # Use 50ms tolerance for per-instrument metrics
            tp, fp, fn = match_onsets(gt_inst_onsets, pred_inst_onsets, 0.05)
            metrics = calculate_metrics(tp, fp, fn)
            
            instrument_name = drum_map.get(pitch, f'Pitch {pitch}')
            per_instrument_results[pitch] = {
                'name': instrument_name,
                'ground_truth_count': len(gt_inst_onsets),
                'predicted_count': len(pred_inst_onsets),
                **metrics
            }
            
            if len(gt_inst_onsets) > 0:  # Only show instruments in ground truth
                print(f"\n  {instrument_name} (MIDI {pitch}):")
                print(f"    Ground truth: {len(gt_inst_onsets)} hits")
                print(f"    Predicted:    {len(pred_inst_onsets)} hits")
                print(f"    Precision:    {metrics['precision']:.4f}")
                print(f"    Recall:       {metrics['recall']:.4f}")
                print(f"    F1-Score:     {metrics['f1_score']:.4f}")
    
    results['per_instrument'] = per_instrument_results
    
    print(f"\n{'='*70}\n")
    
    return results

def batch_evaluate(ground_truth_dir, predicted_dir, output_file="evaluation_results.json"):
    """
    Evaluate all MIDI files in directories
    """
    print(f"{'='*80}")
    print(f"  BATCH ONSET DETECTION EVALUATION")
    print(f"{'='*80}")
    
    gt_files = sorted(Path(ground_truth_dir).glob('*.mid'))
    
    all_results = []
    
    for gt_file in gt_files:
        # Find corresponding predicted file
        pred_file = Path(predicted_dir) / gt_file.name
        
        if not pred_file.exists():
            print(f"\n⚠️  Warning: No predicted file for {gt_file.name}")
            continue
        
        # Evaluate
        result = evaluate_onset_detection(str(gt_file), str(pred_file))
        all_results.append(result)
    
    # Calculate average metrics
    print(f"\n{'='*80}")
    print(f"  AVERAGE METRICS ACROSS ALL FILES")
    print(f"{'='*80}")
    
    for tolerance_ms in [25, 50, 100]:
        tolerance_key = f'{tolerance_ms}ms'
        
        precisions = [r['tolerance_levels'][tolerance_key]['precision'] 
                     for r in all_results]
        recalls = [r['tolerance_levels'][tolerance_key]['recall'] 
                  for r in all_results]
        f1_scores = [r['tolerance_levels'][tolerance_key]['f1_score'] 
                    for r in all_results]
        
        print(f"\n  Tolerance: ±{tolerance_ms}ms")
        print(f"    Avg Precision: {np.mean(precisions):.4f} (±{np.std(precisions):.4f})")
        print(f"    Avg Recall:    {np.mean(recalls):.4f} (±{np.std(recalls):.4f})")
        print(f"    Avg F1-Score:  {np.mean(f1_scores):.4f} (±{np.std(f1_scores):.4f})")
    
    # Save results
    summary = {
        'evaluation_date': str(np.datetime64('now')),
        'ground_truth_dir': ground_truth_dir,
        'predicted_dir': predicted_dir,
        'num_files': len(all_results),
        'individual_results': all_results,
        'average_metrics': {
            '25ms': {
                'precision': float(np.mean([r['tolerance_levels']['25ms']['precision'] for r in all_results])),
                'recall': float(np.mean([r['tolerance_levels']['25ms']['recall'] for r in all_results])),
                'f1_score': float(np.mean([r['tolerance_levels']['25ms']['f1_score'] for r in all_results]))
            },
            '50ms': {
                'precision': float(np.mean([r['tolerance_levels']['50ms']['precision'] for r in all_results])),
                'recall': float(np.mean([r['tolerance_levels']['50ms']['recall'] for r in all_results])),
                'f1_score': float(np.mean([r['tolerance_levels']['50ms']['f1_score'] for r in all_results]))
            },
            '100ms': {
                'precision': float(np.mean([r['tolerance_levels']['100ms']['precision'] for r in all_results])),
                'recall': float(np.mean([r['tolerance_levels']['100ms']['recall'] for r in all_results])),
                'f1_score': float(np.mean([r['tolerance_levels']['100ms']['f1_score'] for r in all_results]))
            }
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    print(f"{'='*80}\n")
    
    return summary

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate drum onset detection')
    parser.add_argument('--ground-truth', required=True, help='Ground truth MIDI file or directory')
    parser.add_argument('--predicted', required=True, help='Predicted MIDI file or directory')
    parser.add_argument('--output', default='evaluation_results.json', help='Output JSON file')
    parser.add_argument('--tolerances', nargs='+', type=int, default=[25, 50, 100],
                       help='Tolerance windows in milliseconds')
    
    args = parser.parse_args()
    
    if os.path.isfile(args.ground_truth) and os.path.isfile(args.predicted):
        # Single file evaluation
        results = evaluate_onset_detection(args.ground_truth, args.predicted, args.tolerances)
        
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"✓ Results saved to: {args.output}")
    
    elif os.path.isdir(args.ground_truth) and os.path.isdir(args.predicted):
        # Batch evaluation
        results = batch_evaluate(args.ground_truth, args.predicted, args.output)
    
    else:
        print("Error: Inputs must be both files or both directories")
