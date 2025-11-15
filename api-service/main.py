"""
API Service - Handles uploads and job management
No ML dependencies, just FastAPI + Cloud Storage
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage, pubsub_v1
import uuid
import json
import os
from datetime import datetime
from typing import Optional
from pathlib import Path
from dataclasses import dataclass
from fastapi.responses import JSONResponse

# ---------------------------
# Load environment variables from .env file (if exists)
# ---------------------------
try:
    from dotenv import load_dotenv
    # Load .env from api-service/.env or project root
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
# Configuration
# ---------------------------


@dataclass
class Settings:
    """API service configuration loaded from environment variables."""
    use_cloud_storage: bool = os.getenv("USE_CLOUD_STORAGE", "true").lower() == "true"
    gcs_bucket_name: str = os.getenv("GCS_BUCKET_NAME", "groovesheet-jobs")
    worker_topic: str = os.getenv("WORKER_TOPIC", "groovesheet-worker-tasks")
    local_jobs_dir: str = os.getenv("LOCAL_JOBS_DIR", "/app/jobs")
    gcp_project: str = os.getenv("GCP_PROJECT", "groovesheet2025")


settings = Settings()

# ---------------------------
# FastAPI App Setup
# ---------------------------

app = FastAPI(title="Groovesheet API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Cloud Storage / Local Storage Setup
# ---------------------------

storage_client = None
bucket = None
publisher = None
topic_path = None

if settings.use_cloud_storage:
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(settings.gcs_bucket_name)
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(settings.gcp_project, settings.worker_topic)
        print(f"✓ Using Cloud Storage: {settings.gcs_bucket_name}")
    except Exception as e:
        print(f"⚠️  Failed to init GCS, falling back to local: {e}")
        settings.use_cloud_storage = False

if not settings.use_cloud_storage:
    os.makedirs(settings.local_jobs_dir, exist_ok=True)
    os.makedirs(f"{settings.local_jobs_dir}/uploads", exist_ok=True)
    print(f"✓ Using local storage: {settings.local_jobs_dir}")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "api"}


@app.post("/api/v1/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None)
):
    """Upload audio file and start transcription job"""
    
    # Validate auth (Clerk JWT) - relaxed for testing
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No authorization header or invalid format")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Create job metadata
    job_data = {
        "job_id": job_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "filename": file.filename,
        "progress": 0
    }
    
    if settings.use_cloud_storage:
        # Upload audio file to GCS
        audio_blob = bucket.blob(f"jobs/{job_id}/input.mp3")
        audio_blob.upload_from_file(file.file, content_type=file.content_type)
        
        # Save job metadata to GCS
        job_blob = bucket.blob(f"jobs/{job_id}/metadata.json")
        job_blob.upload_from_string(json.dumps(job_data), content_type="application/json")
        
        # Publish message to worker topic
        message_data = json.dumps({"job_id": job_id, "bucket": settings.gcs_bucket_name}).encode("utf-8")
        future = publisher.publish(topic_path, message_data)
        message_id = future.result()  # Wait for publish to complete
        print(f"✓ Published job {job_id} to topic {settings.worker_topic}, message ID: {message_id}")
        print(f"✓ Topic path: {topic_path}")
    else:
        # Local mode: save to filesystem
        job_dir = f"{settings.local_jobs_dir}/{job_id}"
        os.makedirs(job_dir, exist_ok=True)
        
        # Save audio file
        audio_path = f"{job_dir}/input.mp3"
        with open(audio_path, "wb") as f:
            f.write(await file.read())
        
        # Save job metadata
        with open(f"{job_dir}/metadata.json", "w") as f:
            json.dump(job_data, f)
        
        print(f"✓ Job {job_id} saved locally to {job_dir}")
    
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/v1/status/{job_id}")
async def get_status(job_id: str):
    """Get job status"""
    
    if settings.use_cloud_storage:
        # Read job metadata from GCS
        job_blob = bucket.blob(f"jobs/{job_id}/metadata.json")
        
        if not job_blob.exists():
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_data = json.loads(job_blob.download_as_text())
    else:
        # Read from local filesystem
        metadata_path = f"{settings.local_jobs_dir}/{job_id}/metadata.json"
        
        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=404, detail="Job not found")
        
        with open(metadata_path, "r") as f:
            job_data = json.load(f)
    
    # Include a conventional download URL hint when completed
    if job_data.get("status") == "completed":
        job_data.setdefault("download_url", f"/api/v1/download/{job_id}")
    # Disable caching so clients always see latest metadata
    return JSONResponse(content=job_data, headers={
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
    })


@app.get("/api/v1/download/{job_id}")
async def download_result(job_id: str):
    """Download MusicXML result"""
    from fastapi.responses import Response
    
    if settings.use_cloud_storage:
        result_blob = bucket.blob(f"jobs/{job_id}/output.musicxml")
        
        if not result_blob.exists():
            raise HTTPException(status_code=404, detail="Result not found")
        
        content = result_blob.download_as_bytes()
    else:
        # Read from local filesystem
        output_path = f"{settings.local_jobs_dir}/{job_id}/output.musicxml"
        
        if not os.path.exists(output_path):
            raise HTTPException(status_code=404, detail="Result not found")
        
        with open(output_path, "rb") as f:
            content = f.read()
    
    return Response(
        content=content,
        media_type="application/vnd.recordare.musicxml+xml",
        headers={"Content-Disposition": f"attachment; filename={job_id}.musicxml"}
    )
