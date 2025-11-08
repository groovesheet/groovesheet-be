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

app = FastAPI(title="Groovesheet API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GCS Setup
USE_CLOUD = os.getenv("USE_CLOUD_STORAGE", "true").lower() == "true"
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "groovesheet-jobs")
WORKER_TOPIC = os.getenv("WORKER_TOPIC", "groovesheet-worker-tasks")
LOCAL_JOBS_DIR = "./jobs"

storage_client = None
bucket = None
publisher = None
topic_path = None

if USE_CLOUD:
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(os.getenv("GCP_PROJECT", "groovesheet2025"), WORKER_TOPIC)
        print(f"✓ Using Cloud Storage: {BUCKET_NAME}")
    except Exception as e:
        print(f"⚠️  Failed to init GCS, falling back to local: {e}")
        USE_CLOUD = False

if not USE_CLOUD:
    os.makedirs(LOCAL_JOBS_DIR, exist_ok=True)
    os.makedirs(f"{LOCAL_JOBS_DIR}/uploads", exist_ok=True)
    print(f"✓ Using local storage: {LOCAL_JOBS_DIR}")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "api"}


@app.post("/api/v1/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None)
):
    """Upload audio file and start transcription job"""
    
    # Validate auth (Clerk JWT)
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")
    
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
    
    if USE_CLOUD:
        # Upload audio file to GCS
        audio_blob = bucket.blob(f"jobs/{job_id}/input.mp3")
        audio_blob.upload_from_file(file.file, content_type=file.content_type)
        
        # Save job metadata to GCS
        job_blob = bucket.blob(f"jobs/{job_id}/metadata.json")
        job_blob.upload_from_string(json.dumps(job_data), content_type="application/json")
        
        # Publish message to worker topic
        message_data = json.dumps({"job_id": job_id, "bucket": BUCKET_NAME}).encode("utf-8")
        publisher.publish(topic_path, message_data)
    else:
        # Local mode: save to filesystem
        job_dir = f"{LOCAL_JOBS_DIR}/{job_id}"
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
    
    if USE_CLOUD:
        # Read job metadata from GCS
        job_blob = bucket.blob(f"jobs/{job_id}/metadata.json")
        
        if not job_blob.exists():
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_data = json.loads(job_blob.download_as_text())
    else:
        # Read from local filesystem
        metadata_path = f"{LOCAL_JOBS_DIR}/{job_id}/metadata.json"
        
        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=404, detail="Job not found")
        
        with open(metadata_path, "r") as f:
            job_data = json.load(f)
    
    return job_data


@app.get("/api/v1/download/{job_id}")
async def download_result(job_id: str):
    """Download MusicXML result"""
    from fastapi.responses import Response
    
    if USE_CLOUD:
        result_blob = bucket.blob(f"jobs/{job_id}/output.musicxml")
        
        if not result_blob.exists():
            raise HTTPException(status_code=404, detail="Result not found")
        
        content = result_blob.download_as_bytes()
    else:
        # Read from local filesystem
        output_path = f"{LOCAL_JOBS_DIR}/{job_id}/output.musicxml"
        
        if not os.path.exists(output_path):
            raise HTTPException(status_code=404, detail="Result not found")
        
        with open(output_path, "rb") as f:
            content = f.read()
    
    return Response(
        content=content,
        media_type="application/vnd.recordare.musicxml+xml",
        headers={"Content-Disposition": f"attachment; filename={job_id}.musicxml"}
    )
