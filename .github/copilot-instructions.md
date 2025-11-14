---
applyTo: 'agent'
---

# GrooveSheet: AI Drum Transcription Platform

## Architecture Overview

**The Critical Dependency Problem**: This project navigates a TensorFlow 2.5.0 + protobuf 3.9.2 compatibility constraint that shapes the entire architecture. Modern `google-cloud-storage` requires `protobuf>=3.19.5`, creating an irreconcilable conflict.

**Solution**: Microservices architecture splits concerns:
- **API Service** (`api-service/`): FastAPI + modern Cloud Storage (no TensorFlow)
- **Worker Service** (`worker-service/`): TensorFlow 2.5.0 + AnNOTEator + Demucs (uses old GCS 1.42.3)
- **Communication**: Google Cloud Pub/Sub (topic: `groovesheet-worker-tasks`, subscription: `groovesheet-worker-tasks-sub`)

**Legacy Monolith** (`backend/`): Original all-in-one service still exists but being phased out. DO NOT add new features here.

### Critical Success Factors for Production

⚠️ **MUST HAVE for microservices to work:**
1. **Worker min-instances=1**: Must stay running to listen for Pub/Sub messages
2. **Worker CPU always on**: `--no-cpu-throttling` flag prevents ML processing hangs
3. **Limited Demucs workers**: `DEMUCS_NUM_WORKERS=1` prevents Cloud Run container overload
4. **Correct Pub/Sub config**: API publishes to `groovesheet-worker-tasks`, worker subscribes to `groovesheet-worker-tasks-sub`
5. **WORKER_TOPIC env var**: API service MUST have this set to publish jobs

## Processing Pipeline

**Flow**: Frontend → API Service → Pub/Sub → Worker Service → GCS → Frontend

1. **Upload** (`POST /api/v1/transcribe`): API saves MP3 to `gs://groovesheet-jobs/jobs/{job_id}/input.mp3`, publishes to Pub/Sub
2. **Processing**: Worker pulls message, runs: Audio → Demucs (drum extraction) → AnNOTEator (ML transcription) → MusicXML output
3. **Progress Updates**: 30% → 35% (Demucs start) → 55% (Demucs done) → 65% (preprocessing) → 80% (prediction) → 90% (sheet music) → 95% (MusicXML saved) → 97% (percussion fix) → 100% (complete)
4. **Polling** (`GET /api/v1/transcribe/{job_id}`): Frontend uses infinite polling with exponential backoff (2s → 30s max)
5. **Download** (`GET /api/v1/transcribe/{job_id}/download`): Auto-triggered when status=completed

**Core Service**: `AnNOTEatorService` (`worker-service/annoteator_service.py`)
- Method: `transcribe_audio(audio_path, output_name, song_title, use_demucs=True)`
- Always call with `use_demucs=True` for drum-only audio
- Returns: `(musicxml_path, metadata)` tuple
- Uses TensorFlow 2.5.0 model: `AnNOTEator/inference/pretrained_models/annoteators/complete_network.h5`
- Provides 7 granular progress checkpoints for real-time updates

## Critical Environment Setup

**Python**: MUST be 3.8 (TensorFlow 2.5.0 requirement)

**Docker Platform**: `--platform=linux/amd64` (macOS compatibility)

**Required Environment Variables**:

**API Service**:
```bash
GCS_BUCKET_NAME=groovesheet-jobs
GCP_PROJECT=groovesheet2025
USE_CLOUD_STORAGE=true
WORKER_TOPIC=groovesheet-worker-tasks  # CRITICAL: Required for Pub/Sub publish
```

**Worker Service**:
```bash
USE_CLOUD_STORAGE=true
GCS_BUCKET_NAME=groovesheet-jobs
WORKER_SUBSCRIPTION=groovesheet-worker-tasks-sub
GCP_PROJECT=groovesheet2025
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python  # Critical for TF 2.5.0
LOG_LEVEL=INFO
DEMUCS_DEVICE=cpu
TF_CPP_MIN_LOG_LEVEL=3  # Suppress TF warnings
OMP_NUM_THREADS=4
DEMUCS_NUM_WORKERS=1  # CRITICAL: Prevents Cloud Run hanging
```

**Docker/Local Development**:
```bash
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python  # Critical for TF 2.5.0
PYTHONPATH=/app/backend:/app/AnNOTEator:/app/demucs:/app/omnizart
TF_CPP_MIN_LOG_LEVEL=3  # Suppress TF warnings
```

**Dependency Installation Order** (see `Dockerfile` lines 35-65):
1. Cython ≥0.29.24
2. numpy==1.19.5
3. tensorflow==2.5.0 + protobuf==3.9.2 (TOGETHER, FIRST)
4. google-cloud-storage==1.42.3 (old version compatible with protobuf 3.9.2)
5. All other requirements
6. Force upgrade typing-extensions≥4.8.0 (last step to fix conflicts)

## Development Workflows

### Local Testing (Microservices)
```powershell
cd groovesheet-be
docker-compose -f docker-compose.microservices.yml up --build
# API: http://localhost:8080, Worker runs background, Pub/Sub emulator on 8085
```

### Local Testing (Legacy Monolith)
```powershell
cd groovesheet-be
docker-compose -f docker-compose.local.yml up --build
# Single service: http://localhost:8080
```

### Cloud Deployment (CRITICAL: Cost Optimization)

**⚠️ NEVER USE CLOUD BUILD - IT'S TOO EXPENSIVE!**

Always build Docker images **locally** and push to GCR. Cloud Build charges are extremely high.

**Deployment Strategy by Change Type:**

1. **Code-only changes** (Python files in `api-service/` or `worker-service/`):
   ```powershell
   .\deploy-scripts\deploy-fast.ps1
   ```
   - Uses optimized `Dockerfile.fast` with code copied LAST
   - Rebuilds in ~5-10 seconds (only last 2 layers)
   - 99% of changes should use this script

2. **Dependency changes** (requirements.txt, new libraries):
   ```powershell
   .\deploy-scripts\local-build-push-deploy.ps1
   ```
   - Full rebuild (~5 minutes)
   - Use ONLY when requirements.txt changes

3. **Deploy-only** (image already pushed to GCR):
   ```powershell
   .\deploy-scripts\deploy-only.ps1
   ```
   - Just updates Cloud Run config, no build/push
   - Use for env var changes, memory/CPU adjustments

**Available Scripts:**
- `deploy-fast.ps1` - **DEFAULT**: Fast code-only deployment (5-10 sec rebuilds)
- `local-build-push-deploy.ps1` - Full rebuild for dependency changes
- `deploy-only.ps1` - Deploy existing image (no rebuild)
- `cloud-build-deploy.ps1` - ❌ DEPRECATED (too expensive, never use)

**Cloud Run Configuration**:
- **API Service** (`groovesheet-api`):
  - Memory: 512Mi-1GB, CPU: 0.5-1
  - Min instances: 0 (scales to zero)
  - Max instances: 100
  - Allow unauthenticated: YES
  - Region: asia-southeast1
  
- **Worker Service** (`groovesheet-worker`):
  - Memory: 32GB, CPU: 8 cores
  - Min instances: 1 (CRITICAL - always running)
  - Max instances: 3
  - Concurrency: 1 (one job per container)
  - Timeout: 3600s (1 hour)
  - CPU throttling: DISABLED (`--no-cpu-throttling`)
  - Allow unauthenticated: NO
  - Region: asia-southeast1

**Current Production Images**:
- API: `gcr.io/groovesheet2025/groovesheet-api:latest`
- Worker: `gcr.io/groovesheet2025/groovesheet-worker:latest`
- GCS Bucket: `groovesheet-jobs`
- Pub/Sub Topic: `groovesheet-worker-tasks`
- Pub/Sub Subscription: `groovesheet-worker-tasks-sub`

### Running Tests
Test scripts live in `groovesheet-be/test-scripts/` (NEVER create test scripts elsewhere):
```powershell
.\test-scripts\test-microservices-local.ps1     # Full local stack
.\test-scripts\test-with-mp3.ps1                # Upload test with sample MP3
.\test-scripts\diagnose-worker.ps1              # Worker debugging
```

## Project-Specific Patterns

### File Organization
- **Test scripts**: `groovesheet-be/test-scripts/` ONLY
- **Deployment scripts**: `groovesheet-be/deploy-scripts/` (note: existing scripts use `deployment-scripts` typo)
- **Job storage**: `shared-jobs/{job-id}/` (GCS: `gs://groovesheet-jobs/jobs/{job-id}/`)
- **Baseline experiments**: `groovesheet-be/Baselines/` (ML model evaluation scripts)

### AnNOTEator Integration
Import pattern (ALWAYS add AnNOTEator to sys.path first):
```python
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "AnNOTEator"))
from inference.input_transform import drum_to_frame
from inference.prediction import predict_drumhit
from inference.transcriber import drum_transcriber
```

### MusicXML Percussion Fix
All MusicXML output MUST have PercussionClef + Drumset on MIDI channel 10:
```python
from music21 import clef, instrument
part.insert(0, clef.PercussionClef())
drums = instrument.Instrument()
drums.instrumentName = "Drumset"
drums.midiProgram = 0
drums.midiChannel = 9  # MIDI channel 10 (0-indexed)
part.insert(0, drums)
```
See `Baselines/Baseline_annoteator_convert_wav_to_musicxml.py:fix_percussion_setup()` for reference.

### Job Metadata Structure
```json
{
  "job_id": "uuid",
  "status": "queued|processing|completed|failed",
  "created_at": "ISO timestamp",
  "filename": "original.mp3",
  "progress": 0-100
}
```

## External Dependencies

**Embedded ML Projects** (DO NOT modify these):
- `AnNOTEator/`: Drum transcription ML model (TensorFlow 2.5.0)
- `demucs/`: Facebook Research drum separation (PyTorch 1.13.1)
- `omnizart/`: Alternative transcription (not actively used)
- `crepe/`: Pitch detection (not actively used)

**GCP Services**:
- Cloud Run (API + Worker containers)
- Cloud Storage (bucket: `groovesheet-jobs`)
- Pub/Sub (topic: `groovesheet-worker-tasks`, sub: `groovesheet-worker-tasks-sub`)

## Common Pitfalls

❌ **DON'T**: Use Cloud Build for deployment (extremely expensive)
❌ **DON'T**: Install tensorflow + google-cloud-storage together without version pinning
❌ **DON'T**: Use Python 3.9+ (TensorFlow 2.5.0 incompatible)
❌ **DON'T**: Add features to `backend/` monolith (legacy code)
❌ **DON'T**: Create test scripts outside `test-scripts/` directory
❌ **DON'T**: Generate summary .md files unless explicitly requested
❌ **DON'T**: Forget `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` in Docker/Cloud Run
❌ **DON'T**: Import heavy ML libraries (librosa, pandas, TensorFlow) inside functions - import at module level

✅ **DO**: Use `deploy-fast.ps1` for all code-only changes (5-10 second rebuilds)
✅ **DO**: Use `AnNOTEatorService.transcribe_audio()` with `use_demucs=True`
✅ **DO**: Check `docker-compose.microservices.yml` for working config examples
✅ **DO**: Reference `PROCESSING_PIPELINE_COMPARISON.md` for monolith vs worker differences
✅ **DO**: Use absolute paths for Windows PowerShell compatibility
✅ **DO**: Set platform to `linux/amd64` in Dockerfiles
✅ **DO**: Import ML libraries at module level (once per container startup, not per job)

## Frontend Integration

React frontend (`groovesheet-fe/`): Separate repository/deployment
- Endpoint: `POST /api/v1/transcribe` (upload MP3)
- Polling: `GET /api/v1/transcribe/{job_id}` (infinite polling with exponential backoff)
- Download: `GET /api/v1/transcribe/{job_id}/download` (auto-triggered on completion)
- Auth: Clerk JWT via Authorization header
- Local dev: `npm start` (port 3000)

### Frontend Polling Behavior
- **Infinite polling**: No timeouts (polls until completion or user cancels)
- **Exponential backoff**: 2s → 4s → 8s → 16s → max 30s on errors
- **Resets to 2s**: On successful responses
- **Auto-download**: Automatically downloads MusicXML when status=completed
- **Progress display**: Shows real-time updates (35% → 100%)