# Groovesheet Microservices Architecture - WORKING CONFIGURATION

## Why Microservices?

**Problem**: TensorFlow 2.5.0 requires `protobuf==3.9.2`, but modern `google-cloud-storage` requires `protobuf>=3.19.5`. They're incompatible.

**Solution**: Split into two services:
- **API Service**: FastAPI + modern Cloud Storage (no TensorFlow/ML dependencies)  
- **Worker Service**: TensorFlow 2.5.0 + AnNOTEator + Demucs + old GCS 1.42.3 (compatible dependencies)

## CRITICAL SUCCESS FACTORS

⚠️ **MUST HAVE for this to work:**
1. **Worker min-instances=1**: `gcloud run services update annoteator-worker --min-instances=1`
2. **Worker CPU always on**: `--no-cpu-throttling` 
3. **Limited Demucs workers**: `DEMUCS_NUM_WORKERS=1` (prevents Cloud Run hanging)
4. **Correct Pub/Sub topic**: API publishes to `groovesheet-worker-tasks`, worker subscribes to `groovesheet-worker-tasks-sub`
5. **Python 3.8**: Critical for TensorFlow 2.5.0 compatibility
6. **Dependency order**: Install TF 2.5.0 + protobuf 3.9.2 FIRST, then old GCS

## Architecture

```
Frontend → API Service (groovesheet-api) → Google Cloud Storage 
    ↓           ↓
   Poll      Pub/Sub Topic (groovesheet-worker-tasks)
    ↑           ↓
Download ← Worker Service (annoteator-worker) ← Pub/Sub Subscription (groovesheet-worker-tasks-sub)
```

### Detailed Flow:
1. **Frontend uploads MP3** → `POST /api/v1/transcribe`
2. **API Service**:
   - Saves MP3 → `gs://groovesheet-jobs/jobs/{job_id}/input.mp3`
   - Creates metadata → `gs://groovesheet-jobs/jobs/{job_id}/metadata.json` 
   - Publishes message → Pub/Sub topic `groovesheet-worker-tasks`
   - Returns job_id to frontend
3. **Worker Service** (always running with min-instances=1):
   - Pulls message from subscription `groovesheet-worker-tasks-sub`
   - Downloads MP3 from GCS
   - **Processing Pipeline**: Demucs (drum separation) → AnNOTEator (ML transcription)
   - **Progress Updates**: 30% (start) → 35% (Demucs start) → 55% (Demucs done) → 65% (preprocessing) → 80% (prediction) → 90% (sheet music) → 95% (MusicXML saved) → 97% (percussion fix) → 100% (complete)
   - Updates metadata with progress + uploads result MusicXML → GCS

## Critical Configuration Details

### Environment Variables (COMPLETE SET)

**API Service** (`groovesheet-api`):
```bash
GCS_BUCKET_NAME=groovesheet-jobs
GCP_PROJECT=groovesheet2025
USE_CLOUD_STORAGE=true
WORKER_TOPIC=groovesheet-worker-tasks   # CRITICAL: Required for Pub/Sub publish
```

**Worker Service** (`annoteator-worker`):
```bash
USE_CLOUD_STORAGE=true
GCS_BUCKET_NAME=groovesheet-jobs
WORKER_SUBSCRIPTION=groovesheet-worker-tasks-sub
GCP_PROJECT=groovesheet2025
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python    # CRITICAL: TF 2.5.0 compatibility
LOG_LEVEL=INFO
DEMUCS_DEVICE=cpu
TF_CPP_MIN_LOG_LEVEL=3                           # Suppress TF warnings
OMP_NUM_THREADS=4
DEMUCS_NUM_WORKERS=1                             # CRITICAL: Prevents Cloud Run hanging
```

### Current Production Images & Versions
- **API**: `gcr.io/groovesheet2025/groovesheet-api:latest` (revision: groovesheet-api-00005-gp5)
- **Worker**: `gcr.io/groovesheet2025/annoteator-worker:latest`
- **GCS Bucket**: `groovesheet-jobs`
- **Pub/Sub Topic**: `groovesheet-worker-tasks`
- **Pub/Sub Subscription**: `groovesheet-worker-tasks-sub`

### Resource Configuration (PROVEN WORKING)

**API Service**:
- Memory: 512Mi (default)
- CPU: 0.5 (default)
- Min instances: 0 (scales to zero)
- Max instances: 100 (default)
- Concurrency: 1000 (default)

**Worker Service** (CRITICAL SETTINGS):
- Memory: 32Gi (required for ML models)
- CPU: 8 (required for processing)
- Min instances: 1 (CRITICAL: must stay running for Pub/Sub)
- Max instances: 3 (limit concurrent processing)
- Concurrency: 1 (CRITICAL: one job per container)
- Timeout: 3600s (1 hour for complex processing)
- CPU throttling: DISABLED (--no-cpu-throttling flag)

### Progress Tracking (7 Granular Checkpoints)
The system now provides detailed progress updates:
- 35%: Demucs drum extraction completed
- 55%: Audio preprocessing done
- 65%: Spectrogram features computed  
- 80%: ML prediction generated
- 90%: Onset extraction completed
- 95%: MusicXML generation started
- 97%: Sheet music assembled
- 100%: File upload and download URL ready
   - Acks Pub/Sub message
4. **Frontend polling**: `GET /api/v1/status/{job_id}` (no timeout, exponential backoff)
5. **Auto-download**: When status=completed, frontend downloads via `GET /api/v1/download/{job_id}`

## Frontend Integration

### Status Polling (NO MORE TIMEOUTS!)
The frontend now uses **resilient infinite polling** with exponential backoff:
- Polls `/api/v1/transcribe/{job_id}` every 2s initially
- Doubles interval on errors (2s → 4s → 8s → 16s, max 30s)
- Resets to 2s on successful responses
- **Never times out** - polls until completion or user cancels

### Auto-Download
- When status reaches 100%, **automatically triggers download**
- Downloads from `/api/v1/transcribe/{job_id}/download`
- File saved as `{original_filename}_transcription.musicxml`
- No manual click required

### Example Response Format
```json
{
  "job_id": "uuid",
  "status": "completed", 
  "progress": 100,
  "filename": "drums.mp3",
  "download_url": "https://groovesheet-api-url/api/v1/transcribe/uuid/download",
  "created_at": "2025-01-13T10:30:00Z",
  "completed_at": "2025-01-13T10:35:00Z"
}
```

## CURRENT WORKING DEPLOYMENT

### Cloud Run Services (asia-southeast1)

**API Service** (`groovesheet-api`):
```bash
# Current revision: groovesheet-api-00005-gp5
# Image: gcr.io/groovesheet2025/groovesheet-api:latest
# Memory: Default (512MB-1GB)
# CPU: Default (0.5-1 CPU)
# Min instances: 0 (scales to zero)
# Allow unauthenticated: YES
```

**Worker Service** (`annoteator-worker`):
```bash
# Image: gcr.io/groovesheet2025/annoteator-worker:latest
# Memory: 32GB
# CPU: 8 cores
# Min instances: 1 (CRITICAL - always running)
# CPU throttling: DISABLED (--no-cpu-throttling)
# Allow unauthenticated: NO
# Timeout: 3600s (1 hour)
# Concurrency: 1 (one job at a time)
```

### Environment Variables

**API Service**:
```bash
GCS_BUCKET_NAME=groovesheet-jobs
GCP_PROJECT=groovesheet2025
USE_CLOUD_STORAGE=true
WORKER_TOPIC=groovesheet-worker-tasks  # CRITICAL - was missing initially
```

**Worker Service**:
```bash
USE_CLOUD_STORAGE=true
GCS_BUCKET_NAME=groovesheet-jobs
WORKER_SUBSCRIPTION=groovesheet-worker-tasks-sub
GCP_PROJECT=groovesheet2025
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python  # CRITICAL for TF 2.5.0
LOG_LEVEL=INFO
DEMUCS_DEVICE=cpu
TF_CPP_MIN_LOG_LEVEL=3
OMP_NUM_THREADS=4
DEMUCS_NUM_WORKERS=1  # CRITICAL - prevents hanging
```

### Pub/Sub Configuration

**Topic**: `projects/groovesheet2025/topics/groovesheet-worker-tasks`
**Subscription**: `projects/groovesheet2025/subscriptions/groovesheet-worker-tasks-sub`
- Ack deadline: 600s
- Message retention: 7 days
- TTL: 31 days

## EXACT DEPLOYMENT COMMANDS (WORKING)

### Prerequisites
```bash
# Ensure you're authenticated and have the right project
gcloud auth login
gcloud config set project groovesheet2025
gcloud auth configure-docker gcr.io
```

### 1. Create Pub/Sub (one-time setup)
```bash
# Create topic
gcloud pubsub topics create groovesheet-worker-tasks --project=groovesheet2025

# Create subscription  
gcloud pubsub subscriptions create groovesheet-worker-tasks-sub \
  --topic=groovesheet-worker-tasks \
  --project=groovesheet2025
```

### 2. Deploy API Service
```bash
cd groovesheet-be

# Build and push API image locally (avoid expensive Cloud Build)
docker build --platform=linux/amd64 -t gcr.io/groovesheet2025/groovesheet-api:latest -f api-service/Dockerfile api-service
docker push gcr.io/groovesheet2025/groovesheet-api:latest

# Deploy to Cloud Run
gcloud run deploy groovesheet-api \
  --image gcr.io/groovesheet2025/groovesheet-api:latest \
  --platform managed \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars "GCS_BUCKET_NAME=groovesheet-jobs,GCP_PROJECT=groovesheet2025,USE_CLOUD_STORAGE=true,WORKER_TOPIC=groovesheet-worker-tasks" \
  --project=groovesheet2025
```

### 3. Deploy Worker Service  
```bash
# Use optimized fast deployment script for code changes
./deploy-scripts/deploy-fast.ps1

# OR manual deployment:
docker build --platform=linux/amd64 -t gcr.io/groovesheet2025/annoteator-worker:latest -f annoteator-worker/Dockerfile.fast .
docker push gcr.io/groovesheet2025/annoteator-worker:latest

gcloud run deploy annoteator-worker \
  --image gcr.io/groovesheet2025/annoteator-worker:latest \
  --platform managed \
  --region asia-southeast1 \
  --memory 32Gi \
  --cpu 8 \
  --no-cpu-throttling \
  --timeout 3600 \
  --concurrency 1 \
  --min-instances 1 \
  --max-instances 3 \
  --no-allow-unauthenticated \
  --set-env-vars "USE_CLOUD_STORAGE=true,GCS_BUCKET_NAME=groovesheet-jobs,WORKER_SUBSCRIPTION=groovesheet-worker-tasks-sub,GCP_PROJECT=groovesheet2025,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,LOG_LEVEL=INFO,DEMUCS_DEVICE=cpu,TF_CPP_MIN_LOG_LEVEL=3,OMP_NUM_THREADS=4,DEMUCS_NUM_WORKERS=1" \
  --project=groovesheet2025
```

### 4. Critical: Set Min Instances (if not done above)
```bash
# Ensure worker stays running to listen for Pub/Sub messages
gcloud run services update annoteator-worker \
  --region=asia-southeast1 \
  --min-instances=1 \
  --project=groovesheet2025
```

## TROUBLESHOOTING

### Common Issues & Solutions

**Worker not processing jobs**:
1. Check min-instances: `gcloud run services describe annoteator-worker --region=asia-southeast1`
2. Worker must have min-instances=1, otherwise Cloud Run shuts it down
3. Check worker logs: `gcloud logging read "resource.labels.service_name=annoteator-worker" --limit=20`

**API not publishing messages**:
1. Ensure WORKER_TOPIC env var is set in API service
2. Check API logs for "Published job" messages
3. Verify Pub/Sub permissions

**Frontend timeout**:
1. Frontend now uses infinite polling with exponential backoff (no more timeouts)
2. Check browser console for polling logs
3. Verify API status endpoint returns proper progress updates

### Verification Commands
```bash
# Check Pub/Sub setup
gcloud pubsub topics list --filter="name:groovesheet-worker-tasks"
gcloud pubsub subscriptions list --filter="name:groovesheet-worker-tasks-sub"

# Check for pending messages (should be empty during normal operation)
gcloud pubsub subscriptions pull groovesheet-worker-tasks-sub --limit=5

# Check service URLs
gcloud run services list --filter="SERVICE_NAME:(groovesheet-api OR annoteator-worker)"

# Monitor logs
gcloud logging read "resource.labels.service_name=groovesheet-api" --limit=10
gcloud logging read "resource.labels.service_name=annoteator-worker" --limit=10
```

## Key Fixes That Made It Work

### 1. Cloud Run CPU Throttling (CRITICAL)
**Problem**: Demucs ML processing would hang indefinitely on Cloud Run
**Solution**: Added `--no-cpu-throttling` flag to worker service
```bash
gcloud run deploy annoteator-worker --no-cpu-throttling
```

### 2. Demucs Worker Limits (CRITICAL) 
**Problem**: Parallel processing overwhelmed Cloud Run containers
**Solution**: Limited to single worker via `DEMUCS_NUM_WORKERS=1`
- Modified `AnNOTEator/inference/input_transform.py`
- Environment variable controls `apply_model(num_workers=)`

### 3. Missing Pub/Sub Topic Environment Variable
**Problem**: API service couldn't publish jobs (missing WORKER_TOPIC)
**Solution**: Added `WORKER_TOPIC=groovesheet-worker-tasks` to API env vars

### 4. Worker Container Persistence (CRITICAL)
**Problem**: Worker shuts down after job completion, can't receive new Pub/Sub messages  
**Solution**: Set `--min-instances=1` to keep worker running constantly
```bash
gcloud run services update groovesheet-worker --min-instances=1
```

### 5. Frontend Timeout Issues
**Problem**: 60-second timeout caused abandonment of successful jobs
**Solution**: Implemented infinite polling with exponential backoff
- Removed all timeouts from frontend
- Added resilient error handling
- Auto-download on completion

### 6. Progress Visibility
**Problem**: Users had no insight into 2-3 minute processing time
**Solution**: Added 7 granular progress checkpoints (35% → 100%)
- Real-time metadata updates to GCS
- Frontend displays current processing step
- Builds user confidence during long processing

## Benefits

✅ **No dependency conflicts** - Each service has its own environment
✅ **Independent scaling** - Scale API and workers separately
✅ **Better reliability** - API stays fast, workers can retry
✅ **Cost efficient** - Workers only run when processing jobs (min-instances=1)
✅ **Progress tracking** - Real-time updates with granular checkpoints
✅ **Auto-download** - Seamless user experience with infinite polling
✅ **Proven working** - Current production system handles 2-3 min processing reliably

## Migration from Monolith

Your existing code mostly stays the same:
- `backend/app/services/audio_processor.py` → Used by worker
- `backend/app/api/routes/transcription.py` → Replaced by `api-service/main.py`
- Frontend changes minimal → Same API endpoints, same flow
