"""
Worker Service - Processes audio files with Omnizart + Demucs
Listens to Pub/Sub, downloads from GCS, processes, uploads results
"""
import os
import json
import tempfile
import shutil
from google.cloud import storage, pubsub_v1
from concurrent.futures import TimeoutError
import logging

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


def process_job(job_id: str, bucket_name: str):
    """Process a single job"""
    logger.info(f"Processing job {job_id}")
    
    bucket = storage_client.bucket(bucket_name)
    
    # Update status to processing
    update_job_status(bucket, job_id, "processing", 10)
    
    try:
        # Download input file
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.mp3")
            audio_blob = bucket.blob(f"jobs/{job_id}/input.mp3")
            audio_blob.download_to_filename(input_path)
            
            # Process audio with ANoteator
            annoteator = AnNOTEatorService(output_dir=temp_dir)
            update_job_status(bucket, job_id, "processing", 30)
            
            # Get job metadata for song title
            job_blob = bucket.blob(f"jobs/{job_id}/metadata.json")
            job_data = json.loads(job_blob.download_as_text())
            
            result_path, result_metadata = annoteator.transcribe_audio(
                audio_path=input_path,
                output_name="output",
                song_title=job_data.get('filename', 'Drum Transcription'),
                use_demucs=True
            )
            
            update_job_status(bucket, job_id, "processing", 90)
            
            # Upload result
            result_blob = bucket.blob(f"jobs/{job_id}/output.musicxml")
            result_blob.upload_from_filename(result_path)
            
            # Update status to completed
            update_job_status(bucket, job_id, "completed", 100)
            logger.info(f"Job {job_id} completed successfully")
            
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        update_job_status(bucket, job_id, "failed", 0, str(e))


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
    try:
        data = json.loads(message.data.decode("utf-8"))
        job_id = data["job_id"]
        bucket_name = data["bucket"]
        
        process_job(job_id, bucket_name)
        message.ack()
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        message.nack()


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
    import threading
    
    # Start health check server in background thread (required for Cloud Run)
    health_thread = threading.Thread(target=health_check_server, daemon=True)
    health_thread.start()
    logger.info("Health check server started")
    
    logger.info(f"Worker starting, listening to {subscription_path}")
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    logger.info("Worker is listening for messages...")
    
    try:
        streaming_pull_future.result()
    except TimeoutError:
        streaming_pull_future.cancel()
        streaming_pull_future.result()


if __name__ == "__main__":
    main()
