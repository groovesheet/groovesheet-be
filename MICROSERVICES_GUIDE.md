# Groovesheet Microservices Architecture Guide

## 📚 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Current Services](#current-services)
3. [Communication Patterns](#communication-patterns)
4. [Deployment Guide](#deployment-guide)
5. [Adding New Services](#adding-new-services)
6. [Standards & Best Practices](#standards--best-practices)
7. [Local Development](#local-development)
8. [Cloud Deployment](#cloud-deployment)

---

## 🏗️ Architecture Overview

Groovesheet uses a **microservices architecture** with the following design principles:

```
┌─────────────┐
│   Client    │
│  (Frontend) │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────────────────────────────────────────┐
│          API Service (FastAPI)                   │
│  - Handles HTTP requests                        │
│  - File uploads to GCS                          │
│  - Job management                               │
│  - Authentication (Clerk JWT)                   │
└──────┬──────────────────────────────────────────┘
       │ Pub/Sub Message
       ▼
┌─────────────────────────────────────────────────┐
│      Google Cloud Pub/Sub (Message Queue)       │
│  Topic: groovesheet-worker-tasks                │
└──────┬──────────────────────────────────────────┘
       │ Pull Subscription
       ▼
┌─────────────────────────────────────────────────┐
│       Worker Service (Python)                    │
│  - Listens to Pub/Sub                          │
│  - Downloads from GCS                           │
│  - Processes audio (ML models)                  │
│  - Uploads results to GCS                       │
└─────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│    Google Cloud Storage (Object Storage)        │
│  Bucket: groovesheet-jobs                       │
│  Structure:                                     │
│    jobs/{job_id}/                               │
│      ├── input.mp3                              │
│      ├── metadata.json                          │
│      └── output.musicxml                        │
└─────────────────────────────────────────────────┘
```

### Key Benefits
- **Separation of Concerns**: API handles requests, Worker handles compute
- **Scalability**: Workers can scale independently based on queue depth
- **Reliability**: Pub/Sub ensures message delivery, retry on failure
- **Cost Efficiency**: API runs continuously, Workers scale to zero when idle
- **No ML Dependencies in API**: Faster startup, smaller container

---

## 🚀 Current Services

### 1. API Service
**Path**: `api-service/`  
**Technology**: FastAPI (Python)  
**Port**: 8080  
**Purpose**: Handle client requests and job orchestration

**Key Features**:
- ✅ File upload handling
- ✅ Job creation & status management
- ✅ Authentication (Clerk JWT validation)
- ✅ CORS middleware for frontend
- ✅ Health check endpoint
- ✅ GCS integration for file storage
- ✅ Pub/Sub publishing for worker tasks

**Dockerfile**: `api-service/Dockerfile`
```dockerfile
FROM python:3.11-slim
# Lightweight, no ML dependencies
# FastAPI, google-cloud-storage, google-cloud-pubsub
```

**Environment Variables**:
```bash
USE_CLOUD_STORAGE=true          # true for GCS, false for local
GCS_BUCKET_NAME=groovesheet-jobs
GCP_PROJECT=groovesheet2025
WORKER_TOPIC=groovesheet-worker-tasks
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
```

---

### 2. Worker Service
**Path**: `worker-service/`  
**Technology**: Python 3.8 + TensorFlow 2.5.0  
**Purpose**: Audio processing with ML models

**Key Features**:
- ✅ Pub/Sub subscription listener
- ✅ Demucs drum extraction (4-model ensemble)
- ✅ AnNOTEator neural network (TensorFlow)
- ✅ MusicXML generation
- ✅ Progress tracking & error handling
- ✅ Automatic retry on failure
- ✅ Graceful shutdown

**Dockerfile**: `worker-service/Dockerfile`
```dockerfile
FROM python:3.8-slim
# Heavy ML dependencies:
# - TensorFlow 2.5.0
# - Demucs
# - librosa, madmom, music21
# - protobuf 3.9.2 (critical for TensorFlow 2.5.0)
```

**Environment Variables**:
```bash
USE_CLOUD_STORAGE=true
GCS_BUCKET_NAME=groovesheet-jobs
GCP_PROJECT=groovesheet2025
WORKER_SUBSCRIPTION=groovesheet-worker-tasks-sub
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json

# Critical for TensorFlow 2.5.0 + protobuf compatibility
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# Performance tuning
DEMUCS_DEVICE=cpu               # cpu or cuda
TF_CPP_MIN_LOG_LEVEL=3          # Suppress TensorFlow warnings
LOG_LEVEL=INFO
```

**Resource Requirements**:
```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 8G
    reservations:
      cpus: '2.0'
      memory: 4G
```

---

## 🔄 Communication Patterns

### 1. Request Flow (Production)
```
1. Client uploads audio → API Service
2. API validates JWT → Returns 401 if invalid
3. API generates job_id → UUID
4. API uploads file to GCS → jobs/{job_id}/input.mp3
5. API creates metadata → jobs/{job_id}/metadata.json
6. API publishes message → Pub/Sub topic
   Message: {"job_id": "...", "bucket": "groovesheet-jobs"}
7. Worker pulls message → Processes
8. Worker updates status → metadata.json (processing → completed/failed)
9. Worker uploads output → jobs/{job_id}/output.musicxml
10. Client polls status → GET /api/v1/jobs/{job_id}
```

### 2. Local Development Flow
```
1. Client uploads audio → API Service
2. API saves file → ./shared-jobs/{job_id}/input.mp3
3. API creates metadata → ./shared-jobs/{job_id}/metadata.json
4. Worker polls directory → Finds new job
5. Worker processes → Same as production
6. Worker saves output → ./shared-jobs/{job_id}/output.musicxml
7. Worker updates metadata → status: "completed"
```

### 3. Message Format (Pub/Sub)
```json
{
  "job_id": "46ca6c51-c9a9-4357-bf8f-e4fba64a98d5",
  "bucket": "groovesheet-jobs"
}
```

### 4. Metadata Format (GCS/Filesystem)
```json
{
  "job_id": "46ca6c51-c9a9-4357-bf8f-e4fba64a98d5",
  "status": "completed",
  "created_at": "2025-11-08T14:37:34.000Z",
  "filename": "song.mp3",
  "progress": 100,
  "result": {
    "total_notes": 1102,
    "bpm": 117.45,
    "duration_seconds": 278.41
  }
}
```

---

## 📦 Deployment Guide

### Cloud Run Deployment (Recommended)

#### 1. Build & Push Images
```bash
# API Service (lightweight, fast)
cd api-service
gcloud builds submit --tag gcr.io/groovesheet2025/api-service:latest

# Worker Service (heavy, infrequent updates)
cd worker-service
gcloud builds submit --tag gcr.io/groovesheet2025/worker-service:latest
```

#### 2. Deploy API Service
```bash
gcloud run deploy api-service \
  --image gcr.io/groovesheet2025/api-service:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars USE_CLOUD_STORAGE=true \
  --set-env-vars GCS_BUCKET_NAME=groovesheet-jobs \
  --set-env-vars GCP_PROJECT=groovesheet2025 \
  --set-env-vars WORKER_TOPIC=groovesheet-worker-tasks
```

#### 3. Deploy Worker Service
```bash
gcloud run deploy worker-service \
  --image gcr.io/groovesheet2025/worker-service:latest \
  --region us-central1 \
  --platform managed \
  --no-allow-unauthenticated \
  --memory 8Gi \
  --cpu 4 \
  --min-instances 0 \
  --max-instances 5 \
  --concurrency 1 \
  --timeout 900s \
  --set-env-vars USE_CLOUD_STORAGE=true \
  --set-env-vars GCS_BUCKET_NAME=groovesheet-jobs \
  --set-env-vars GCP_PROJECT=groovesheet2025 \
  --set-env-vars WORKER_SUBSCRIPTION=groovesheet-worker-tasks-sub \
  --set-env-vars PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
  --set-env-vars DEMUCS_DEVICE=cpu \
  --set-env-vars TF_CPP_MIN_LOG_LEVEL=3
```

#### 4. Setup Pub/Sub Push Subscription
```bash
# Create topic
gcloud pubsub topics create groovesheet-worker-tasks

# Create push subscription to trigger worker
gcloud pubsub subscriptions create groovesheet-worker-tasks-sub \
  --topic groovesheet-worker-tasks \
  --push-endpoint https://worker-service-XXXXX-uc.a.run.app/process \
  --ack-deadline 600
```

#### 5. Create GCS Bucket
```bash
gsutil mb -c STANDARD -l us-central1 gs://groovesheet-jobs
gsutil lifecycle set lifecycle.json gs://groovesheet-jobs
```

**lifecycle.json** (Auto-delete old jobs):
```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 30}
      }
    ]
  }
}
```

---

## ➕ Adding New Services

### Service Standards Checklist

#### ✅ Required Structure
```
new-service/
├── Dockerfile           # Container definition
├── main.py             # Service entrypoint
├── requirements.txt    # Python dependencies
└── README.md           # Service documentation
```

#### ✅ Dockerfile Template
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    <dependencies> \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=5)"

# Run application
CMD ["python", "main.py"]
```

#### ✅ FastAPI Template
```python
"""
New Service - Brief description
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="New Service")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
SERVICE_NAME = os.getenv("SERVICE_NAME", "new-service")
GCS_BUCKET = os.getenv("GCS_BUCKET_NAME", "groovesheet-jobs")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": SERVICE_NAME}

@app.post("/api/v1/endpoint")
async def process_request(data: dict):
    """Main processing endpoint"""
    try:
        # Your logic here
        result = {"status": "success"}
        return result
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

#### ✅ Environment Variables Standard
```bash
# Naming convention: {SERVICE_NAME}_{VARIABLE}
NEW_SERVICE_API_KEY=xxx
NEW_SERVICE_BUCKET=yyy

# Shared variables (use same names across services)
GCS_BUCKET_NAME=groovesheet-jobs
GCP_PROJECT=groovesheet2025
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
LOG_LEVEL=INFO
```

#### ✅ Docker Compose Entry
```yaml
new-service:
  build:
    context: ./new-service
    dockerfile: Dockerfile
  ports:
    - "8081:8080"
  environment:
    - SERVICE_NAME=new-service
    - GCS_BUCKET_NAME=groovesheet-jobs
    - GCP_PROJECT=groovesheet2025
  volumes:
    - ./credentials.json:/app/credentials.json:ro
  depends_on:
    - api
  networks:
    - groovesheet
```

---

## 🎯 Standards & Best Practices

### 1. Service Communication
- **API Gateway Pattern**: All client requests go through API service
- **Async Communication**: Use Pub/Sub for worker tasks (not HTTP)
- **Shared Storage**: Use GCS as single source of truth
- **No Direct Service-to-Service HTTP**: Prevents coupling

### 2. Error Handling
```python
# API Service - Return user-friendly errors
try:
    result = process()
except Exception as e:
    logger.error(f"Failed to process: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Processing failed")

# Worker Service - Retry with backoff
from google.api_core.retry import Retry
retry = Retry(predicate=lambda e: True, initial=1.0, maximum=60.0)
```

### 3. Logging Format
```python
# Standard format across all services
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Use structured logging for Cloud Logging
logger.info("Processing job", extra={
    "job_id": job_id,
    "status": "processing",
    "progress": 50
})
```

### 4. Health Checks
```python
@app.get("/health")
async def health():
    """Health check for load balancer"""
    return {
        "status": "healthy",
        "service": "api-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }
```

### 5. Security
```python
# API Service - JWT validation
from fastapi import Header, HTTPException
import jwt

async def verify_jwt(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "Missing authorization")
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, CLERK_PUBLIC_KEY, algorithms=["RS256"])
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
```

### 6. Resource Management
```yaml
# Set appropriate limits for each service type
api-service:
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 512Mi

worker-service:
  deploy:
    resources:
      limits:
        cpus: '4.0'
        memory: 8Gi
```

### 7. Container Optimization
```dockerfile
# Multi-stage builds for smaller images
FROM python:3.11 as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
```

---

## 🔧 Local Development

### Option 1: Docker Compose (Recommended)
```bash
# Start all services
docker-compose -f docker-compose.local.yml up

# Start specific service
docker-compose -f docker-compose.local.yml up worker

# Rebuild after code changes
docker-compose -f docker-compose.local.yml up --build
```

### Option 2: Direct Python
```bash
# API Service
cd api-service
pip install -r requirements.txt
python main.py

# Worker Service
cd worker-service
pip install -r requirements.txt
python worker_local.py
```

### Testing
```bash
# Upload file
curl -X POST http://localhost:8080/api/v1/transcribe \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.mp3"

# Check job status
curl http://localhost:8080/api/v1/jobs/{job_id}

# Health check
curl http://localhost:8080/health
```

---

## ☁️ Cloud Deployment

### CI/CD Pipeline (GitHub Actions)
```yaml
name: Deploy Services

on:
  push:
    branches: [main]

jobs:
  deploy-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - name: Build and Push
        run: |
          gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT }}/api-service:${{ github.sha }}
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy api-service \
            --image gcr.io/${{ secrets.GCP_PROJECT }}/api-service:${{ github.sha }} \
            --region us-central1

  deploy-worker:
    runs-on: ubuntu-latest
    steps:
      # Similar to api-service
```

### Monitoring
```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Monitor metrics
gcloud monitoring dashboards create --config-from-file dashboard.json
```

### Scaling
```bash
# Auto-scale based on CPU
gcloud run services update api-service \
  --min-instances 1 \
  --max-instances 10 \
  --cpu-throttling

# Scale workers based on queue depth
gcloud run services update worker-service \
  --min-instances 0 \
  --max-instances 5 \
  --concurrency 1
```

---

## 📊 Service Integration Example

### Scenario: Add Notation Cleanup Service

**Purpose**: Post-process MusicXML to fix notation errors

**Integration Steps**:

1. **Create Service Structure**
```bash
mkdir cleanup-service
cd cleanup-service
touch Dockerfile main.py requirements.txt
```

2. **Define Communication**
```python
# API Service publishes to new topic after worker completes
publisher.publish("groovesheet-cleanup-tasks", {
    "job_id": job_id,
    "musicxml_path": f"jobs/{job_id}/output.musicxml"
})

# Cleanup Service subscribes
subscriber = pubsub_v1.SubscriberClient()
subscription = subscriber.subscription_path(PROJECT_ID, "cleanup-sub")
```

3. **Update docker-compose**
```yaml
cleanup-service:
  build: ./cleanup-service
  environment:
    - CLEANUP_SUBSCRIPTION=groovesheet-cleanup-tasks-sub
```

4. **Deploy**
```bash
gcloud run deploy cleanup-service \
  --image gcr.io/groovesheet2025/cleanup-service:latest \
  --memory 512Mi
```

---

## 🚨 Common Issues & Solutions

### Issue 1: Worker Not Processing Jobs
**Check**:
```bash
# Verify subscription exists
gcloud pubsub subscriptions describe groovesheet-worker-tasks-sub

# Check worker logs
gcloud logging read "resource.type=cloud_run_revision resource.labels.service_name=worker-service"
```

### Issue 2: Out of Memory
**Solution**:
```bash
# Increase worker memory
gcloud run services update worker-service --memory 16Gi
```

### Issue 3: Slow Cold Starts
**Solution**:
```bash
# Keep minimum instances
gcloud run services update worker-service --min-instances 1
```

---

## 📚 References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Cloud Run](https://cloud.google.com/run/docs)
- [Google Cloud Pub/Sub](https://cloud.google.com/pubsub/docs)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Microservices Patterns](https://microservices.io/patterns/)

---

**Last Updated**: November 8, 2025  
**Maintainer**: Groovesheet Team  
**Version**: 1.0.0
