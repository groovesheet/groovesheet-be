import os
import json
import glob
import tempfile
import threading
import time
import logging
import sys
from dataclasses import dataclass
from typing import Optional, Tuple
from pathlib import Path

from http.server import HTTPServer, BaseHTTPRequestHandler

# ---------------------------
# Load environment variables from .env file (if exists)
# ---------------------------
try:
    from dotenv import load_dotenv
    # Load .env from project root (annoteator-worker/.env) or current directory
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment variables from {env_path}")
    else:
        # Try parent directory (project root)
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded environment variables from {env_path}")
except ImportError:
    # python-dotenv not installed, skip
    pass

# ---------------------------
# Stdout/Stderr: unbuffered
# ---------------------------

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

# ---------------------------
# Config (load early for logging level)
# ---------------------------


@dataclass
class Settings:
    """Worker service configuration loaded from environment variables."""
    use_cloud_storage: bool = os.getenv("USE_CLOUD_STORAGE", "true").lower() == "true"
    project_id: str = os.getenv("GCP_PROJECT", "groovesheet2025")
    subscription_id: str = os.getenv("WORKER_SUBSCRIPTION", "groovesheet-worker-tasks-sub")
    local_jobs_dir: str = os.getenv("LOCAL_JOBS_DIR", "/app/testing/local-jobs")
    port: int = int(os.getenv("PORT", "8080"))
    # ML/Processing settings
    tf_cpp_min_log_level: str = os.getenv("TF_CPP_MIN_LOG_LEVEL", "3")
    demucs_device: str = os.getenv("DEMUCS_DEVICE", "cpu")
    demucs_num_workers: int = int(os.getenv("DEMUCS_NUM_WORKERS", "1"))
    omp_num_threads: int = int(os.getenv("OMP_NUM_THREADS", "4"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    protocol_buffers_implementation: str = os.getenv(
        "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python"
    )

    def __post_init__(self):
        """Apply environment variable settings to os.environ for libraries."""
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = self.tf_cpp_min_log_level
        os.environ["OMP_NUM_THREADS"] = str(self.omp_num_threads)
        os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = self.protocol_buffers_implementation


settings = Settings()

# ---------------------------
# Logging (after settings are loaded)
# ---------------------------

log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ---------------------------
# Health Check HTTP Server
# ---------------------------


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP health check endpoint for Cloud Run"""

    def do_GET(self):
        if self.path in ("/health", "/"):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default HTTP logs
        pass


def start_health_server(port: int):
    """Start HTTP server for Cloud Run health checks"""
    try:
        logger.info(f"Attempting to start health server on 0.0.0.0:{port}")
        sys.stdout.flush()

        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        logger.info(f"✓ Health check server bound to port {port}")
        sys.stdout.flush()

        server.serve_forever()
    except Exception as e:
        logger.error(f"Health server failed to start: {e}", exc_info=True)
        sys.stdout.flush()
        raise


# ---------------------------
# Domain Logic: Transcription
# ---------------------------

# Import your service AFTER basic setup

from services.annoteator_service import AnNOTEatorService


def run_transcription(
    audio_path: str,
    output_dir: str,
    song_title: str,
) -> Tuple[str, dict]:
    """
    Shared transcription logic for both cloud and local jobs.
    Returns (result_path, result_metadata).
    """
    logger.info("Creating AnNOTEatorService")
    annoteator = AnNOTEatorService(output_dir=output_dir)

    logger.info("Starting transcription...")
    logger.info(f"  Input file: {audio_path}")
    logger.info(f"  Output directory: {output_dir}")
    logger.info(f"  Song title: {song_title}")
    logger.info(f"  File exists: {os.path.exists(audio_path)}")
    logger.info(f"  File size: {os.path.getsize(audio_path)} bytes")
    sys.stdout.flush()

    logger.info("Progress: 30%")
    logger.info("ABOUT TO CALL annoteator.transcribe_audio()...")
    sys.stdout.flush()

    try:
        result_path, result_metadata = annoteator.transcribe_audio(
            audio_path=str(audio_path),
            output_name="output",
            song_title=song_title,
            use_demucs=True,
        )

        logger.info("annoteator.transcribe_audio() returned successfully!")
        sys.stdout.flush()

        return result_path, result_metadata
    except Exception as e:
        logger.error(f"Error during transcription: {e}", exc_info=True)
        sys.stdout.flush()
        raise


# ---------------------------
# Cloud Mode Implementation
# ---------------------------

if settings.use_cloud_storage:
    from google.cloud import storage, pubsub_v1

    storage_client = storage.Client()
    subscriber = pubsub_v1.SubscriberClient()


class CloudJobProcessor:
    """Handles a single job in Cloud (GCS) mode."""

    def __init__(self, storage_client: "storage.Client"):
        self.storage_client = storage_client

    def _load_metadata(self, metadata_blob) -> Tuple[dict, str]:
        """Load metadata JSON and extract song title with robust decoding."""
        if not metadata_blob.exists():
            return {}, "Drum Transcription"

        try:
            # Try UTF-8 first
            metadata = json.loads(metadata_blob.download_as_text())
            song_title = metadata.get("filename", "Drum Transcription")
            return metadata, song_title
        except UnicodeDecodeError:
            metadata_bytes = metadata_blob.download_as_bytes()
            metadata = json.loads(metadata_bytes.decode("utf-8", errors="replace"))
            song_title = metadata.get("filename", "Drum Transcription")
            return metadata, song_title

    def process_job(self, job_id: str, bucket_name: str):
        """Process job from Cloud Storage."""
        bucket = self.storage_client.bucket(bucket_name)

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.mp3")
            audio_blob = bucket.blob(f"jobs/{job_id}/input.mp3")
            metadata_blob = bucket.blob(f"jobs/{job_id}/metadata.json")

            # Download audio
            audio_blob.download_to_filename(input_path)
            logger.info(f"Downloaded input file for job {job_id}")
            sys.stdout.flush()

            # Load metadata + song title
            metadata, song_title = self._load_metadata(metadata_blob)

            # Transcribe
            result_path, _ = run_transcription(
                audio_path=input_path,
                output_dir=temp_dir,
                song_title=song_title,
            )

            # Upload result
            result_blob = bucket.blob(f"jobs/{job_id}/output.musicxml")
            result_blob.upload_from_filename(result_path)

            # Update metadata
            metadata["status"] = "completed"
            metadata["progress"] = 100
            metadata_blob.upload_from_string(
                json.dumps(metadata), content_type="application/json"
            )

            logger.info(f"Job {job_id} completed successfully")


class CloudWorker:
    """Subscribes to Pub/Sub and processes jobs using CloudJobProcessor."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.processor = CloudJobProcessor(storage_client)

        self.subscription_path = subscriber.subscription_path(
            self.settings.project_id, self.settings.subscription_id
        )

    def _callback(self, message: "pubsub_v1.subscriber.message.Message"):
        try:
            data = json.loads(message.data.decode("utf-8"))
            job_id = data["job_id"]
            bucket_name = data["bucket"]

            logger.info(f"Received message for job {job_id}")
            self.processor.process_job(job_id, bucket_name)
            message.ack()
            logger.info(f"Acknowledged message for job {job_id}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            message.nack()

    def run_forever(self):
        logger.info(f"Listening for messages on {self.subscription_path}")
        streaming_pull_future = subscriber.subscribe(
            self.subscription_path, callback=self._callback
        )

        try:
            streaming_pull_future.result()
        except KeyboardInterrupt:
            streaming_pull_future.cancel()
            logger.info("Cloud worker stopped")


# ---------------------------
# Local Mode Implementation
# ---------------------------


class LocalJobProcessor:
    """Handles jobs from the local filesystem."""

    def __init__(self, jobs_dir: str):
        self.jobs_dir = jobs_dir

    def process_job_dir(self, job_dir: str):
        job_id = os.path.basename(job_dir)
        logger.info(f"Processing job {job_id}")

        metadata_path = os.path.join(job_dir, "metadata.json")
        input_path = os.path.join(job_dir, "input.mp3")
        output_path = os.path.join(job_dir, "output.musicxml")

        # Skip invalid jobs
        if not os.path.exists(metadata_path):
            logger.debug(f"Skipping {job_id} - not a valid job (no metadata.json)")
            return

        # Skip if already processed
        if os.path.exists(output_path):
            logger.info(f"Job {job_id} already processed, skipping")
            return

        # Read metadata
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        if metadata.get("status") == "completed":
            logger.info(f"Job {job_id} already completed, skipping")
            return

        song_title = metadata.get("filename", "Drum Transcription")

        # Update progress before heavy work
        metadata["progress"] = 30
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Transcribe
        result_path, _ = run_transcription(
            audio_path=input_path,
            output_dir=job_dir,
            song_title=song_title,
        )

        # Mark completed
        metadata["status"] = "completed"
        metadata["progress"] = 100
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        logger.info(f"Job {job_id} completed successfully")


class LocalWorker:
    """Polls the filesystem and processes jobs using LocalJobProcessor."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.processor = LocalJobProcessor(self.settings.local_jobs_dir)

    def run_forever(self, poll_interval: int = 5):
        logger.info(f"Local worker starting, watching {self.settings.local_jobs_dir}")

        while True:
            job_dirs = glob.glob(os.path.join(self.settings.local_jobs_dir, "*"))
            for job_dir in job_dirs:
                if os.path.isdir(job_dir):
                    try:
                        self.processor.process_job_dir(job_dir)
                    except Exception as e:
                        logger.error(f"Error processing {job_dir}: {e}", exc_info=True)
            time.sleep(poll_interval)


# ---------------------------
# Main Entrypoint
# ---------------------------


def main():
    logger.info(f"Starting worker with settings: {settings}")

    # Start health server (only needed in cloud mode)
    if settings.use_cloud_storage:
        logger.info(f"Starting health check server on port {settings.port}...")
        sys.stdout.flush()

        health_thread = threading.Thread(
            target=start_health_server, args=(settings.port,), daemon=True
        )
        health_thread.start()
        time.sleep(2)
        logger.info("Health check server started")
        sys.stdout.flush()

    # Start worker
    if settings.use_cloud_storage:
        logger.info(
            f"Starting in CLOUD mode: project={settings.project_id}, "
            f"subscription={settings.subscription_id}"
        )
        worker = CloudWorker(settings)
        worker.run_forever()
    else:
        logger.info(f"Starting in LOCAL mode: jobs_dir={settings.local_jobs_dir}")
        worker = LocalWorker(settings)
        worker.run_forever()


if __name__ == "__main__":
    main()