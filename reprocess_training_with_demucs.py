"""
Demucs Training Data Reprocessing Pipeline
Process all E-GMD training data through Demucs to match production audio characteristics

⚠️  WARNING: This is EXTREMELY resource-intensive
    - Estimated time: 20-40 hours on high-end workstation
    - Estimated storage: 200-300 GB for processed audio
    - Requires significant CPU/RAM

This addresses the critical issue identified by AnNOTEator team:
"We suggest looking into how the Demucs package generates the extracted drum track,
and in particular, the type of effects or filters that are automatically applied.
Ideally, the training sound clips should receive a similar treatment."
"""

import os
import subprocess
import sys
from pathlib import Path
from tqdm import tqdm
import shutil
import time
import json
from datetime import datetime

def check_requirements():
    """
    Check if Demucs is installed and system has enough resources
    """
    print("🔍 Checking requirements...")
    
    # Check Demucs installation
    try:
        result = subprocess.run(['demucs', '--help'], 
                              capture_output=True, text=True, timeout=10)
        print("✓ Demucs is installed")
    except FileNotFoundError:
        print("✗ Demucs not found. Please install: pip install demucs")
        return False
    except Exception as e:
        print(f"✗ Error checking Demucs: {e}")
        return False
    
    # Check available disk space
    try:
        stat = shutil.disk_usage('.')
        free_gb = stat.free / (1024**3)
        print(f"✓ Available disk space: {free_gb:.1f} GB")
        
        if free_gb < 250:
            print(f"⚠️  WARNING: Low disk space. Recommended: 250+ GB, Available: {free_gb:.1f} GB")
            response = input("Continue anyway? (yes/no): ")
            if response.lower() != 'yes':
                return False
    except Exception as e:
        print(f"⚠️  Could not check disk space: {e}")
    
    return True

def get_demucs_models():
    """
    List available Demucs models
    """
    return {
        'htdemucs': {
            'description': 'Hybrid Transformer Demucs (RECOMMENDED - Latest & Best)',
            'speed': 'Medium',
            'quality': 'Excellent'
        },
        'htdemucs_ft': {
            'description': 'Fine-tuned Hybrid Transformer',
            'speed': 'Medium',
            'quality': 'Excellent+'
        },
        'mdx_extra': {
            'description': 'MDX Challenge Extra model',
            'speed': 'Slow',
            'quality': 'Best (but slowest)'
        },
        'mdx': {
            'description': 'MDX Challenge model',
            'speed': 'Fast',
            'quality': 'Very Good'
        }
    }

def process_single_file(wav_file, output_dir, model_name="htdemucs", save_format="mp3"):
    """
    Process a single WAV file through Demucs
    
    Args:
        wav_file: Path to input WAV file
        output_dir: Output directory
        model_name: Demucs model to use
        save_format: Output format (mp3, wav, flac)
    
    Returns:
        tuple: (success: bool, output_path: str, error_message: str)
    """
    try:
        # Build Demucs command
        cmd = [
            'demucs',
            '--two-stems=drums',  # Only extract drums (faster)
            '-n', model_name,
            '-o', str(output_dir),
        ]
        
        # Add format options
        if save_format == 'mp3':
            cmd.extend(['--mp3', '--mp3-bitrate', '320'])
        elif save_format == 'flac':
            cmd.append('--flac')
        # Default is WAV
        
        cmd.append(str(wav_file))
        
        # Run Demucs
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout per file
        )
        
        if result.returncode != 0:
            return False, None, f"Demucs failed: {result.stderr}"
        
        # Find output file
        # Demucs creates: output_dir/model_name/filename/drums.{format}
        basename = Path(wav_file).stem
        demucs_subdir = Path(output_dir) / model_name / basename
        
        drum_file = demucs_subdir / f"drums.{save_format}"
        
        if not drum_file.exists():
            return False, None, f"Output file not found: {drum_file}"
        
        return True, str(drum_file), None
        
    except subprocess.TimeoutExpired:
        return False, None, "Processing timeout (>10 minutes)"
    except Exception as e:
        return False, None, str(e)

def process_dataset(input_dir, output_dir, model_name="htdemucs", 
                   save_format="mp3", preserve_structure=True):
    """
    Process entire dataset through Demucs
    
    Args:
        input_dir: Input directory containing WAV files
        output_dir: Output directory for processed files
        model_name: Demucs model to use
        save_format: Output format (mp3, wav, flac)
        preserve_structure: Maintain original directory structure
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all WAV files
    print(f"\n📁 Scanning for audio files in: {input_dir}")
    wav_files = list(input_path.rglob("*.wav"))
    
    if len(wav_files) == 0:
        print("✗ No WAV files found!")
        return
    
    print(f"✓ Found {len(wav_files)} audio files")
    
    # Estimate processing time
    avg_time_per_file = 120  # seconds (conservative estimate)
    total_time_hours = (len(wav_files) * avg_time_per_file) / 3600
    
    print(f"\n⏱️  Estimated processing time: {total_time_hours:.1f} hours")
    print(f"   ({avg_time_per_file}s per file × {len(wav_files)} files)")
    print(f"\n⚠️  This will take a LONG time. Consider:")
    print(f"   • Running overnight")
    print(f"   • Using tmux/screen to prevent disconnection")
    print(f"   • Monitoring progress with another terminal")
    
    # Confirm
    print(f"\n" + "="*70)
    print(f"  READY TO START PROCESSING")
    print(f"="*70)
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Model:  {model_name}")
    print(f"Format: {save_format}")
    print(f"Files:  {len(wav_files)}")
    print(f"="*70)
    
    response = input("\nContinue? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Process files
    start_time = time.time()
    successful = 0
    failed = 0
    errors = []
    
    # Create stats file
    stats = {
        'start_time': datetime.now().isoformat(),
        'input_dir': str(input_dir),
        'output_dir': str(output_dir),
        'model': model_name,
        'format': save_format,
        'total_files': len(wav_files),
        'processed': [],
        'failed': []
    }
    
    print(f"\n🚀 Starting processing...\n")
    
    for i, wav_file in enumerate(tqdm(wav_files, desc="Processing", unit="file")):
        # Calculate relative path to preserve structure
        rel_path = wav_file.relative_to(input_path)
        
        if preserve_structure:
            file_output_dir = output_path / rel_path.parent
        else:
            file_output_dir = output_path
        
        file_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process file
        success, output_file, error = process_single_file(
            wav_file, 
            file_output_dir, 
            model_name, 
            save_format
        )
        
        if success:
            successful += 1
            
            # Move and rename output
            final_output = file_output_dir / f"{wav_file.stem}_drums.{save_format}"
            shutil.move(output_file, final_output)
            
            # Clean up Demucs temp directories
            demucs_temp = file_output_dir / model_name
            if demucs_temp.exists():
                shutil.rmtree(demucs_temp)
            
            stats['processed'].append({
                'input': str(wav_file),
                'output': str(final_output),
                'relative_path': str(rel_path)
            })
            
        else:
            failed += 1
            error_info = {
                'file': str(wav_file),
                'error': error
            }
            errors.append(error_info)
            stats['failed'].append(error_info)
            
            tqdm.write(f"✗ Failed: {wav_file.name} - {error}")
        
        # Save stats periodically (every 10 files)
        if (i + 1) % 10 == 0:
            with open(output_path / 'processing_stats.json', 'w') as f:
                json.dump(stats, f, indent=2)
    
    # Final statistics
    end_time = time.time()
    total_time = end_time - start_time
    
    stats['end_time'] = datetime.now().isoformat()
    stats['total_time_seconds'] = total_time
    stats['successful'] = successful
    stats['failed'] = failed
    
    # Save final stats
    with open(output_path / 'processing_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    # Print summary
    print(f"\n" + "="*70)
    print(f"  PROCESSING COMPLETE")
    print(f"="*70)
    print(f"✓ Successful: {successful}/{len(wav_files)} files")
    print(f"✗ Failed:     {failed}/{len(wav_files)} files")
    print(f"⏱️  Total time:  {total_time/3600:.2f} hours")
    print(f"⏱️  Avg per file: {total_time/len(wav_files):.1f} seconds")
    print(f"\n📁 Output directory: {output_dir}")
    print(f"📊 Stats saved to: {output_path / 'processing_stats.json'}")
    
    if failed > 0:
        print(f"\n⚠️  {failed} files failed. Check errors:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"   • {Path(error['file']).name}: {error['error']}")
        if len(errors) > 5:
            print(f"   ... and {len(errors)-5} more (see processing_stats.json)")
    
    print(f"="*70)
    
    return stats

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Process training data through Demucs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process E-GMD dataset with default settings
  python reprocess_training_with_demucs.py \\
      --input AnNOTEator/dataset/e-gmd-v1.0.0 \\
      --output training_data/demucs_processed
  
  # Use best quality model (slower)
  python reprocess_training_with_demucs.py \\
      --input AnNOTEator/dataset/e-gmd-v1.0.0 \\
      --output training_data/demucs_processed \\
      --model mdx_extra \\
      --format flac
  
  # Fast processing with lower quality
  python reprocess_training_with_demucs.py \\
      --input AnNOTEator/dataset/e-gmd-v1.0.0 \\
      --output training_data/demucs_processed \\
      --model mdx \\
      --format mp3
        """
    )
    
    parser.add_argument('--input', required=True,
                       help='Input directory with training audio')
    parser.add_argument('--output', required=True,
                       help='Output directory for processed audio')
    parser.add_argument('--model', default='htdemucs',
                       choices=['htdemucs', 'htdemucs_ft', 'mdx_extra', 'mdx'],
                       help='Demucs model to use (default: htdemucs)')
    parser.add_argument('--format', default='mp3',
                       choices=['mp3', 'wav', 'flac'],
                       help='Output audio format (default: mp3 to save space)')
    parser.add_argument('--no-preserve-structure', action='store_true',
                       help='Do not preserve directory structure')
    
    args = parser.parse_args()
    
    # Print header
    print("="*70)
    print("  DEMUCS TRAINING DATA REPROCESSING PIPELINE")
    print("="*70)
    print("\n🎯 Purpose: Process training data to match production audio")
    print("   AnNOTEator recommendation: Retrain with Demucs-processed audio")
    print("   This addresses the train/production audio mismatch issue\n")
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Show model info
    models = get_demucs_models()
    model_info = models.get(args.model, {})
    print(f"\n📋 Selected model: {args.model}")
    print(f"   {model_info.get('description', 'N/A')}")
    print(f"   Speed: {model_info.get('speed', 'N/A')}")
    print(f"   Quality: {model_info.get('quality', 'N/A')}")
    
    # Process
    stats = process_dataset(
        args.input,
        args.output,
        args.model,
        args.format,
        not args.no_preserve_structure
    )
    
    if stats and stats['successful'] > 0:
        print("\n✅ SUCCESS! You can now retrain AnNOTEator with:")
        print(f"\n   python AnNOTEator/model_development/train_model.py \\")
        print(f"       --dataset {args.output} \\")
        print(f"       --model_name complete_network_demucs \\")
        print(f"       --epochs 100 \\")
        print(f"       --batch_size 32\n")
