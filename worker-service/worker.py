"""
Worker Service - Processes audio files with Omnizart + Demucs
Listens to Pub/Sub, downloads from GCS, processes, uploads results
"""
import os
import json
import tempfile
import shutil
import threading
import time
from google.cloud import storage, pubsub_v1
from concurrent.futures import TimeoutError
import logging
import sys

# Force unbuffered output for Cloud Run logs
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

# Setup logging to match backend format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import processing modules
import sys
sys.path.append('/app/backend')

from app.services.annoteator_service import AnNOTEatorService

# GCS Setup
storage_client = storage.Client()
subscriber = pubsub_v1.SubscriberClient()

PROJECT_ID = os.getenv("GCP_PROJECT", "groovesheet2025")
SUBSCRIPTION_ID = os.getenv("WORKER_SUBSCRIPTION", "groovesheet-worker-tasks-sub")
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

# Track jobs currently being processed to prevent duplicates
processing_jobs = set()
processing_lock = threading.Lock()


def process_job(job_id: str, bucket_name: str):
    """Process a single job"""
    # Check if job is already being processed
    with processing_lock:
        if job_id in processing_jobs:
            logger.warning(f"Job {job_id} is already being processed, skipping duplicate")
            return
        processing_jobs.add(job_id)
    
    try:
        logger.info(f"Starting job {job_id}")
        sys.stdout.flush()
        sys.stderr.flush()
        
        bucket = storage_client.bucket(bucket_name)
        
        # Check job status first - don't reprocess completed/processing jobs
        job_blob = bucket.blob(f"jobs/{job_id}/metadata.json")
        if job_blob.exists():
            try:
                job_data = json.loads(job_blob.download_as_text())
                current_status = job_data.get("status", "")
                
                if current_status in ["completed", "failed"]:
                    logger.info(f"Job {job_id} already {current_status}, skipping")
                    return
                
                if current_status == "processing":
                    logger.warning(f"Job {job_id} already processing, possible duplicate message")
                    # Continue anyway in case previous worker died
            except Exception as e:
                logger.warning(f"Could not read metadata for job {job_id}: {e}")
                # Continue with processing even if metadata read fails
        else:
            logger.info(f"No metadata found for job {job_id}, will create during processing")
        
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Update status to processing
        update_job_status(bucket, job_id, "processing", 10)
        logger.info(f"Updated job {job_id} status to processing")
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Download input file
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.mp3")
            audio_blob = bucket.blob(f"jobs/{job_id}/input.mp3")
            
            if not audio_blob.exists():
                raise FileNotFoundError(f"Input file not found for job {job_id}")
            
            audio_blob.download_to_filename(input_path)
            logger.info(f"Downloaded input file for job {job_id}")
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Process audio with ANoteator
            annoteator = AnNOTEatorService(output_dir=temp_dir)
            update_job_status(bucket, job_id, "processing", 30)
            logger.info(f"AnNOTEatorService initialized, starting transcription")
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Get job metadata for song title
            # Re-fetch the metadata to ensure we have the latest version
            job_blob = bucket.blob(f"jobs/{job_id}/metadata.json")
            if job_blob.exists():
                job_data = json.loads(job_blob.download_as_text())
                song_title = job_data.get('filename', 'Drum Transcription')
            else:
                logger.warning(f"Metadata not found for job {job_id}, using default title")
                song_title = 'Drum Transcription'
            
            logger.info(f"Starting transcription for job {job_id}")
            logger.info(f"  Input file: {input_path}")
            logger.info(f"  Output directory: {temp_dir}")
            logger.info(f"  Song title: {song_title}")
            logger.info(f"  File exists: {os.path.exists(input_path)}")
            logger.info(f"  File size: {os.path.getsize(input_path) if os.path.exists(input_path) else 'N/A'} bytes")
            sys.stdout.flush()
            sys.stderr.flush()
            
            update_job_status(bucket, job_id, "processing", 30)
            logger.info("Progress: 30%")
            logger.info("ABOUT TO CALL annoteator.transcribe_audio()...")
            sys.stdout.flush()
            sys.stderr.flush()
            
            try:
                result_path, result_metadata = annoteator.transcribe_audio(
                    audio_path=str(input_path),
                    output_name="output",
                    song_title=song_title,
                    use_demucs=True
                )
                logger.info("annoteator.transcribe_audio() returned successfully!")
                sys.stdout.flush()
                sys.stderr.flush()
            except Exception as transcribe_error:
                logger.error(f"TRANSCRIBE_AUDIO FAILED: {transcribe_error}", exc_info=True)
                sys.stdout.flush()
                sys.stderr.flush()
                raise
            
            logger.info(f"Transcription returned successfully for job {job_id}")
            sys.stdout.flush()
            sys.stderr.flush()
            
            update_job_status(bucket, job_id, "processing", 90)
            logger.info(f"Transcription complete for job {job_id}, uploading result")
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Upload result
            result_blob = bucket.blob(f"jobs/{job_id}/output.musicxml")
            result_blob.upload_from_filename(result_path)
            
            # Update status to completed
            update_job_status(bucket, job_id, "completed", 100)
            logger.info(f"Job {job_id} completed successfully")
            
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
        try:
            bucket = storage_client.bucket(bucket_name)
            update_job_status(bucket, job_id, "failed", 0, str(e))
        except Exception as update_error:
            logger.error(f"Failed to update status for job {job_id}: {update_error}")
    finally:
        # Remove from processing set
        with processing_lock:
            processing_jobs.discard(job_id)


def update_job_status(bucket, job_id: str, status: str, progress: int, error: str = None):
    """Update job status in GCS"""
    job_blob = bucket.blob(f"jobs/{job_id}/metadata.json")
    
    if job_blob.exists():
        job_data = json.loads(job_blob.download_as_text())
    else:
        job_data = {"job_id": job_id}
    
    job_data["status"] = status
    job_data["progress"] = progress
    if error:
        job_data["error"] = error
    
    job_blob.upload_from_string(json.dumps(job_data), content_type="application/json")


def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    """Process incoming Pub/Sub message"""
    ack_thread = None
    stop_acking = threading.Event()
    
    def extend_ack_deadline():
        """Periodically extend ack deadline while processing"""
        while not stop_acking.is_set():
            try:
                # Extend deadline every 5 minutes (300 seconds)
                time.sleep(300)
                if not stop_acking.is_set():
                    message.modify_ack_deadline(600)  # Extend by 10 minutes
                    logger.info("Extended message ack deadline")
            except Exception as e:
                logger.warning(f"Failed to extend ack deadline: {e}")
    
    try:
        data = json.loads(message.data.decode("utf-8"))
        job_id = data["job_id"]
        bucket_name = data["bucket"]
        
        logger.info(f"Received message for job {job_id}")
        
        # Start background thread to extend ack deadline for long processing
        ack_thread = threading.Thread(target=extend_ack_deadline, daemon=True)
        ack_thread.start()
        logger.info("Started ack deadline extender thread")
        
        # Process the job (this can take 5-10 minutes)
        process_job(job_id, bucket_name)
        
        # Stop the ack extender thread
        stop_acking.set()
        
        # Acknowledge the message after successful processing
        message.ack()
        logger.info(f"Acknowledged message for job {job_id}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid message format: {e}")
        stop_acking.set()
        message.ack()  # Ack invalid messages so they don't retry forever
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        stop_acking.set()
        # Nack the message so it can be retried
        message.nack()
        logger.info(f"Nacked message due to error")


def health_check_server():
    """Simple HTTP server for Cloud Run health checks"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health' or self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status":"healthy","service":"worker"}')
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            # Suppress default logging
            pass
    
    port = int(os.getenv("PORT", "8080"))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"Health check server listening on port {port}")
    server.serve_forever()


def main():
    """Main worker loop"""
    # Start health check server in background thread (required for Cloud Run)
    health_thread = threading.Thread(target=health_check_server, daemon=True)
    health_thread.start()
    logger.info("Health check server started")
    
    logger.info(f"Worker starting, listening to {subscription_path}")
    
    # Configure flow control to process one message at a time
    # This prevents duplicate processing and resource exhaustion
    flow_control = pubsub_v1.types.FlowControl(
        max_messages=1,  # Process one job at a time
        max_bytes=10 * 1024 * 1024,  # 10 MB
    )
    
    streaming_pull_future = subscriber.subscribe(
        subscription_path, 
        callback=callback,
        flow_control=flow_control
    )
    logger.info("Worker is listening for messages (processing one at a time)...")
    
    try:
        streaming_pull_future.result()
    except TimeoutError:
        streaming_pull_future.cancel()
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
        logger.info("Worker shutdown requested")


if __name__ == "__main__":
    main()
