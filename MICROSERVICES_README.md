# Groovesheet Microservices Architecture - WORKING CONFIGURATION

## Why Microservices?

**Problem**: TensorFlow 2.10.0 and librosa 0.9.0+ have complex dependencies that conflict with modern cloud libraries.

**Solution**: Split into two services:
- **API Service**: FastAPI + modern Cloud Storage (no TensorFlow/ML dependencies)  
- **Worker Service**: TensorFlow 2.10.0 + AnNOTEator + Demucs (integrated) + compatible GCS 1.42.3

## Project Structure

```
groovesheet-be/
├── api-service/              # FastAPI API service
│   ├── main.py              # API endpoints
│   ├── Dockerfile           # API container
│   └── requirements.txt     # API dependencies (modern)
│
├── annoteator-worker/       # ML Worker service
│   ├── worker.py            # Worker entrypoint
│   ├── Dockerfile           # Worker container
│   ├── requirements.txt     # Worker dependencies (TF 2.10.0)
│   └── services/
│       └── annoteator_service.py  # AnNOTEator + Demucs integration
│
├── library/                 # Shared ML libraries
│   └── AnNOTEator/         # ML models and inference code
│       └── inference/
│           ├── pretrained_models/  # ML model files (.h5)
│           ├── input_transform.py  # Audio preprocessing + Demucs
│           ├── prediction.py       # ML inference
│           └── transcriber.py      # MusicXML generation
│
├── testing/local-jobs/      # Local development job storage
├── deploy-scripts/          # Deployment automation
├── test-scripts/            # System testing
│   ├── new-system-test.ps1  # Current test script
│   └── README.md            # Testing documentation
│
├── docker-compose.local.yml      # Local testing (no GCP)
└── docker-compose.microservices.yml  # Cloud testing (with GCP)
```

## CRITICAL SUCCESS FACTORS

⚠️ **MUST HAVE for this to work:**
1. **Worker min-instances=1**: `gcloud run services update annoteator-worker --min-instances=1`
2. **Worker CPU always on**: `--no-cpu-throttling` 
3. **Limited Demucs workers**: `DEMUCS_NUM_WORKERS=1` (prevents Cloud Run hanging)
4. **Correct Pub/Sub topic**: API publishes to `groovesheet-worker-tasks`, worker subscribes to `groovesheet-worker-tasks-sub`
5. **Python 3.8**: Critical for TensorFlow 2.10.0 compatibility
6. **Librosa compatibility**: All librosa calls use keyword argument `y=` for audio data (librosa 0.9.0+ requirement)
7. **AnNOTEator model file**: `library/AnNOTEator/inference/pretrained_models/annoteators/complete_network.h5` must exist

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
   - Saves MP3 → `gs://groovesheet-jobs/jobs/{job_id}/input.mp3` (or `testing/local-jobs/{job_id}/` in local mode)
   - Creates metadata → `metadata.json` with status="queued", progress=0
   - **Cloud mode**: Publishes message → Pub/Sub topic `groovesheet-worker-tasks`
   - **Local mode**: Worker polls filesystem directly
   - Returns job_id to frontend
3. **Worker Service** (always running with min-instances=1 in cloud):
   - **Cloud mode**: Pulls message from subscription `groovesheet-worker-tasks-sub`
   - **Local mode**: Polls `testing/local-jobs/` directory for new jobs
   - Downloads MP3 from GCS or reads from local filesystem
   - **Processing Pipeline**: 
     1. Demucs drum extraction (integrated in AnNOTEator)
     2. Audio preprocessing and BPM detection
     3. ML inference with TensorFlow model
     4. MusicXML generation
   - **Progress Updates**: 30% (start) → 35% (Demucs start) → 55% (Demucs done) → 65% (preprocessing) → 80% (prediction) → 90% (sheet music) → 95% (MusicXML saved) → 97% (percussion fix) → 100% (complete)
   - Updates metadata.json with progress + uploads result MusicXML
   - **Cloud mode**: Acks Pub/Sub message when complete

## Critical Configuration Details

### Environment Variables (COMPLETE SET)

**API Service** (`groovesheet-api`):
```bash
# Storage Mode
USE_CLOUD_STORAGE=true              # false for local testing
LOCAL_JOBS_DIR=/app/jobs            # Used when USE_CLOUD_STORAGE=false

# Cloud Configuration
GCS_BUCKET_NAME=groovesheet-jobs
GCP_PROJECT=groovesheet2025
WORKER_TOPIC=groovesheet-worker-tasks   # CRITICAL: Required for Pub/Sub publish
```

**Worker Service** (`annoteator-worker`):
```bash
# Storage Mode  
USE_CLOUD_STORAGE=true              # false for local testing
LOCAL_JOBS_DIR=/app/jobs            # Used when USE_CLOUD_STORAGE=false

# Cloud Configuration
GCS_BUCKET_NAME=groovesheet-jobs
GCP_PROJECT=groovesheet2025
WORKER_SUBSCRIPTION=groovesheet-worker-tasks-sub

# ML/Processing Configuration
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python    # CRITICAL: TF compatibility
LOG_LEVEL=INFO
DEMUCS_DEVICE=cpu
TF_CPP_MIN_LOG_LEVEL=3              # Suppress TensorFlow warnings
OMP_NUM_THREADS=4
DEMUCS_NUM_WORKERS=1                # CRITICAL: Prevents Cloud Run hanging
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

### 1. Demucs Integration (ARCHITECTURE CHANGE)
**Old Approach**: Separate `demucs-worker` microservice
**New Approach**: Demucs integrated directly into `annoteator-worker`
- Demucs is called via `drum_extraction()` in `library/AnNOTEator/inference/input_transform.py`
- Eliminates inter-service communication overhead
- Simpler architecture with only 2 services instead of 3

### 2. Librosa API Compatibility (CRITICAL FIX)
**Problem**: `TypeError: onset_strength() takes 0 positional arguments`
**Cause**: Librosa 0.9.0+ changed API - audio data must be keyword argument
**Solution**: Updated all librosa calls in `input_transform.py`:
```python
# Old (broken)
librosa.onset.onset_strength(drum_track, sr=sample_rate)
librosa.onset.onset_detect(drum_track, onset_envelope=o_env)
librosa.beat.tempo(drum_track, sr=sample_rate)

# New (working)
librosa.onset.onset_strength(y=drum_track, sr=sample_rate)
librosa.onset.onset_detect(y=drum_track, onset_envelope=o_env)
librosa.beat.tempo(y=drum_track, sr=sample_rate)
```

### 3. Directory Structure (LOCAL TESTING)
**Old**: Used `shared-jobs/` directory
**New**: Uses `testing/local-jobs/` directory
- Better organization for local vs cloud testing
- Matches docker-compose.local.yml volume mounts
- Separate from old architecture artifacts

### 4. Cloud Run CPU Throttling (CRITICAL)
**Problem**: Demucs ML processing would hang indefinitely on Cloud Run
**Solution**: Added `--no-cpu-throttling` flag to worker service
```bash
gcloud run deploy annoteator-worker --no-cpu-throttling
```

### 5. Demucs Worker Limits (CRITICAL) 
**Problem**: Parallel processing overwhelmed Cloud Run containers
**Solution**: Limited to single worker via `DEMUCS_NUM_WORKERS=1`
- Environment variable controls parallel processing
- Prevents memory exhaustion and container crashes

### 6. Missing Pub/Sub Topic Environment Variable
**Problem**: API service couldn't publish jobs (missing WORKER_TOPIC)
**Solution**: Added `WORKER_TOPIC=groovesheet-worker-tasks` to API env vars

### 7. Worker Container Persistence (CRITICAL)
**Problem**: Worker shuts down after job completion, can't receive new Pub/Sub messages  
**Solution**: Set `--min-instances=1` to keep worker running constantly
```bash
gcloud run services update annoteator-worker --min-instances=1
```

### 8. Frontend Timeout Issues
**Problem**: 60-second timeout caused abandonment of successful jobs
**Solution**: Implemented infinite polling with exponential backoff
- Removed all timeouts from frontend
- Added resilient error handling
- Auto-download on completion

### 9. Progress Visibility
**Problem**: Users had no insight into 2-3 minute processing time
**Solution**: Added 7 granular progress checkpoints (35% → 100%)
- Real-time metadata updates to GCS/filesystem
- Frontend displays current processing step
- Builds user confidence during long processing

### 10. AnNOTEator Model File
**Problem**: Model file not found at runtime
**Solution**: Ensured `library/AnNOTEator/inference/pretrained_models/annoteators/complete_network.h5` exists
- Added `.gitignore` exception for model files
- Model file (1.92 MB) is committed to repository
- Dockerfile copies entire `library/AnNOTEator` directory

## Benefits

✅ **No dependency conflicts** - Each service has its own environment
✅ **Independent scaling** - Scale API and workers separately
✅ **Better reliability** - API stays fast, workers can retry
✅ **Cost efficient** - Workers only run when processing jobs (min-instances=1)
✅ **Progress tracking** - Real-time updates with granular checkpoints
✅ **Auto-download** - Seamless user experience with infinite polling
✅ **Proven working** - Current production system handles 2-3 min processing reliably
✅ **Local testing** - Full system works locally without GCP (docker-compose.local.yml)
✅ **Simplified architecture** - Only 2 services (API + Worker), Demucs integrated

## Local Development & Testing

### Quick Start (Local Mode)
```bash
# 1. Ensure model file exists
ls library/AnNOTEator/inference/pretrained_models/annoteators/complete_network.h5

# 2. Run test script
cd test-scripts
.\new-system-test.ps1
```

The test script will:
1. Start API + Worker + Pub/Sub emulator via docker-compose
2. Upload test MP3 (`Baseline_Nirvana_Testfile.mp3`)
3. Monitor progress in real-time
4. Download resulting MusicXML
5. Show container logs for debugging

### Docker Compose Files

**docker-compose.local.yml** - For local testing (no GCP needed):
- Uses `USE_CLOUD_STORAGE=false`
- Stores jobs in `testing/local-jobs/`
- Includes Pub/Sub emulator on port 8085
- Worker polls filesystem instead of Pub/Sub

**docker-compose.microservices.yml** - For cloud testing:
- Uses `USE_CLOUD_STORAGE=true`
- Requires `credentials.json`
- Connects to real GCP Pub/Sub
- Tests full cloud integration locally

### Legacy Files (Can Be Deleted)

The following are no longer used in the new architecture:
- ❌ `demucs-worker/` - Demucs now integrated in annoteator-worker
- ❌ `demucs/` - Uses PyPI package instead
- ❌ `shared-jobs/` - Old job storage, now uses `testing/local-jobs/`
- ❌ `test-scripts/test-full-system.ps1` - Old test script
- ❌ `AnNOTEator/` - Empty/redundant, actual code in `library/AnNOTEator/`
- ❌ `testmusic.mp3` - Old test file
- ❌ Test output files (e.g., `test_output_*.musicxml`)

See `test-scripts/README.md` for detailed explanations of what changed.
