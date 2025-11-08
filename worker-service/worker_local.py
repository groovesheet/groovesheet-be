"""
Local Worker - Processes audio files by polling local directory
For testing without Pub/Sub
"""
import os
import json
import time
import logging
import sys
import glob

# Setup logging to match backend format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import processing logic
sys.path.append('/app/backend')
from app.services.annoteator_service import AnNOTEatorService

LOCAL_JOBS_DIR = os.getenv("LOCAL_JOBS_DIR", "/app/jobs")

def process_job(job_dir: str):
    """Process a single job from local filesystem"""
    job_id = os.path.basename(job_dir)
    logger.info(f"Processing job {job_id}")
    
    metadata_path = os.path.join(job_dir, "metadata.json")
    input_path = os.path.join(job_dir, "input.mp3")
    output_path = os.path.join(job_dir, "output.musicxml")
    
    # Check if already processed
    if os.path.exists(output_path):
        logger.info(f"Job {job_id} already processed, skipping")
        return
    
    # Read metadata
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    if metadata.get('status') not in ['queued', 'processing']:
        return
    
    try:
        # Update status to processing
        metadata['status'] = 'processing'
        metadata['progress'] = 10
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
        
        # Process audio with ANoteator
        annoteator = AnNOTEatorService(output_dir=job_dir)
        logger.info(f"Starting drum transcription for {job_id}")
        logger.info(f"Input file: {input_path}")
        logger.info(f"Output directory: {job_dir}")
        
        def update_progress(progress):
            metadata['progress'] = progress
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            logger.info(f"Progress: {progress}%")
        
        # Update progress during processing
        update_progress(30)
        logger.info("Calling annoteator.transcribe_audio...")
        
        try:
            result_path, result_metadata = annoteator.transcribe_audio(
                audio_path=input_path,
                output_name="output",
                song_title=metadata.get('filename', 'Drum Transcription'),
                use_demucs=True
            )
            logger.info(f"Transcription returned: {result_path}")
            update_progress(90)
        except Exception as transcribe_error:
            logger.error(f"Transcription failed with error: {transcribe_error}", exc_info=True)
            raise
        
        # Copy result to output path
        if result_path and os.path.exists(result_path):
            import shutil
            shutil.copy(result_path, output_path)
            
            # Update status to completed
            metadata['status'] = 'completed'
            metadata['progress'] = 100
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            logger.info(f"Job {job_id} completed successfully")
        else:
            raise Exception("Processing did not produce output file")
            
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        metadata['status'] = 'failed'
        metadata['error'] = str(e)
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)


def main():
    """Main worker loop - polls jobs directory"""
    logger.info(f"Local worker starting, watching {LOCAL_JOBS_DIR}")
    
    processed_jobs = set()
    
    while True:
        try:
            # Find all job directories
            job_dirs = glob.glob(os.path.join(LOCAL_JOBS_DIR, "*"))
            
            for job_dir in job_dirs:
                if not os.path.isdir(job_dir):
                    continue
                
                job_id = os.path.basename(job_dir)
                
                # Skip if already processed
                if job_id in processed_jobs:
                    continue
                
                # Check if has metadata and input file
                metadata_path = os.path.join(job_dir, "metadata.json")
                input_path = os.path.join(job_dir, "input.mp3")
                
                if os.path.exists(metadata_path) and os.path.exists(input_path):
                    process_job(job_dir)
                    processed_jobs.add(job_id)
            
            # Sleep before next poll
            time.sleep(5)
            
        except KeyboardInterrupt:
            logger.info("Worker shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in worker loop: {e}", exc_info=True)
            time.sleep(10)


if __name__ == "__main__":
    main()
