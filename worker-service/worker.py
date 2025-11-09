"""
Unified Worker - Handles both Cloud (Pub/Sub) and Local (filesystem) modes
"""
import os
import json
import tempfile
import threading
import time
import logging
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP health check endpoint for Cloud Run"""
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress HTTP logs
        pass


def start_health_server():
    """Start HTTP server for Cloud Run health checks"""
    port = int(os.getenv('PORT', '8080'))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Health check server listening on port {port}")
    server.serve_forever()


# Import processing modules
sys.path.append('/app/backend')
from app.services.annoteator_service import AnNOTEatorService

# Determine mode
USE_CLOUD_STORAGE = os.getenv("USE_CLOUD_STORAGE", "true").lower() == "true"

if USE_CLOUD_STORAGE:
    from google.cloud import storage, pubsub_v1
    storage_client = storage.Client()
    subscriber = pubsub_v1.SubscriberClient()
    PROJECT_ID = os.getenv("GCP_PROJECT", "groovesheet2025")
    SUBSCRIPTION_ID = os.getenv("WORKER_SUBSCRIPTION", "groovesheet-worker-tasks-sub")
    logger.info(f"Starting in CLOUD mode: project={PROJECT_ID}, subscription={SUBSCRIPTION_ID}")
else:
    LOCAL_JOBS_DIR = os.getenv("LOCAL_JOBS_DIR", "/app/shared-jobs")
    logger.info(f"Starting in LOCAL mode: jobs_dir={LOCAL_JOBS_DIR}")


def process_job_cloud(job_id: str, bucket_name: str):
    """Process job from Cloud Storage"""
    import glob
    
    bucket = storage_client.bucket(bucket_name)
    
    # Download and process
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "input.mp3")
        audio_blob = bucket.blob(f"jobs/{job_id}/input.mp3")
        audio_blob.download_to_filename(input_path)
        logger.info(f"Downloaded input file for job {job_id}")
        sys.stdout.flush()
        
        # Get song title
        metadata_blob = bucket.blob(f"jobs/{job_id}/metadata.json")
        if metadata_blob.exists():
            metadata = json.loads(metadata_blob.download_as_text())
            song_title = metadata.get('filename', 'Drum Transcription')
        else:
            song_title = 'Drum Transcription'
        
        # Process
        annoteator = AnNOTEatorService(output_dir=temp_dir)
        logger.info(f"Starting transcription for job {job_id}")
        logger.info(f"  Input file: {input_path}")
        logger.info(f"  Output directory: {temp_dir}")
        logger.info(f"  Song title: {song_title}")
        logger.info(f"  File exists: {os.path.exists(input_path)}")
        logger.info(f"  File size: {os.path.getsize(input_path)} bytes")
        sys.stdout.flush()
        
        logger.info("Progress: 30%")
        logger.info("ABOUT TO CALL annoteator.transcribe_audio()...")
        sys.stdout.flush()
        
        result_path, result_metadata = annoteator.transcribe_audio(
            audio_path=str(input_path),
            output_name="output",
            song_title=song_title,
            use_demucs=True
        )
        
        logger.info("annoteator.transcribe_audio() returned successfully!")
        sys.stdout.flush()
        
        # Upload result
        result_blob = bucket.blob(f"jobs/{job_id}/output.musicxml")
        result_blob.upload_from_filename(result_path)
        
        # Update metadata
        metadata['status'] = 'completed'
        metadata['progress'] = 100
        metadata_blob.upload_from_string(json.dumps(metadata), content_type="application/json")
        
        logger.info(f"Job {job_id} completed successfully")


def process_job_local(job_dir: str):
    """Process job from local filesystem"""
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
    
    if metadata.get('status') == 'completed':
        logger.info(f"Job {job_id} already completed, skipping")
        return
    
    # Process
    annoteator = AnNOTEatorService(output_dir=job_dir)
    logger.info(f"Starting transcription for job {job_id}")
    logger.info(f"  Input file: {input_path}")
    logger.info(f"  Output directory: {job_dir}")
    logger.info(f"  Song title: {metadata.get('filename', 'Drum Transcription')}")
    logger.info(f"  File exists: {os.path.exists(input_path)}")
    logger.info(f"  File size: {os.path.getsize(input_path)} bytes")
    sys.stdout.flush()
    
    metadata['progress'] = 30
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    logger.info("Progress: 30%")
    logger.info("ABOUT TO CALL annoteator.transcribe_audio()...")
    sys.stdout.flush()
    
    result_path, result_metadata = annoteator.transcribe_audio(
        audio_path=input_path,
        output_name="output",
        song_title=metadata.get('filename', 'Drum Transcription'),
        use_demucs=True
    )
    
    logger.info(f"annoteator.transcribe_audio() returned: {result_path}")
    sys.stdout.flush()
    
    metadata['status'] = 'completed'
    metadata['progress'] = 100
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    logger.info(f"Job {job_id} completed successfully")


if __name__ == "__main__":
    # Start health check server in background thread (Cloud Run requirement)
    if USE_CLOUD_STORAGE:
        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()
        time.sleep(1)  # Let health server start
    
    # Run worker loop
    if USE_CLOUD_STORAGE:
        # Cloud mode: Subscribe to Pub/Sub
        def callback(message):
            try:
                data = json.loads(message.data.decode("utf-8"))
                job_id = data["job_id"]
                bucket_name = data["bucket"]
                
                logger.info(f"Received message for job {job_id}")
                process_job_cloud(job_id, bucket_name)
                message.ack()
                logger.info(f"Acknowledged message for job {job_id}")
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                message.nack()
        
        subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
        streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
        logger.info(f"Listening for messages on {subscription_path}")
        
        try:
            streaming_pull_future.result()
        except KeyboardInterrupt:
            streaming_pull_future.cancel()
            logger.info("Worker stopped")
    else:
        # Local mode: Poll filesystem
        import glob
        logger.info(f"Local worker starting, watching {LOCAL_JOBS_DIR}")
        
        while True:
            job_dirs = glob.glob(os.path.join(LOCAL_JOBS_DIR, "*"))
            for job_dir in job_dirs:
                if os.path.isdir(job_dir):
                    try:
                        process_job_local(job_dir)
                    except Exception as e:
                        logger.error(f"Error processing {job_dir}: {e}", exc_info=True)
            
            time.sleep(5)
