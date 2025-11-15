# GrooveSheet Backend - Microservices Architecture

AI-powered drum transcription platform using AnNOTEator and Demucs for converting audio to MusicXML sheet music.

## Architecture

**Microservices Design:**
- **API Service** (`api-service/`): FastAPI + GCS + Pub/Sub publishing
- **Worker Service** (`annoteator-worker/`): TensorFlow 2.5.0 + AnNOTEator + Demucs processing  
- **Communication**: Google Cloud Pub/Sub (`groovesheet-worker-tasks` topic)

## Quick Start

### Local Development
```bash
docker-compose -f docker-compose.microservices.yml up --build
```
- API: http://localhost:8080
- Worker: Background processing via Pub/Sub emulator

### Production Deployment
```bash
# Use fast deployment script for code changes (5-10 second rebuilds)
./deploy-scripts/deploy-fast.ps1

# Full deployment for dependency changes
./deploy-scripts/local-build-push-deploy.ps1
```

## Project Structure

```
groovesheet-be/
├── api-service/              # FastAPI service for job submission
├── annoteator-worker/        # Background processing service  
├── library/                 # Shared libraries
│   └── AnNOTEator/          # Drum transcription ML models
├── demucs/                  # Audio source separation
├── Baselines/               # ML model evaluation scripts
├── deploy-scripts/          # Deployment automation
├── test-scripts/            # Testing utilities
├── testing/                 # Testing utilities and local jobs
│   └── local-jobs/          # Local job storage for testing
└── docker-compose.microservices.yml
```

## Core Technologies

- **Python 3.8** (TensorFlow 2.5.0 requirement)
- **TensorFlow 2.5.0** + **protobuf 3.9.2** (compatibility constraint)
- **Google Cloud**: Run, Storage, Pub/Sub
- **FastAPI** (API service)
- **AnNOTEator** (neural drum transcription)
- **Demucs** (drum separation from full mix)

## Key Features

✅ **Granular Progress Tracking**: 7 checkpoints (35% → 100%)  
✅ **Auto-Download**: Seamless user experience  
✅ **Resilient Processing**: Infinite polling, no timeouts  
✅ **CPU Optimization**: No throttling for ML workloads  
✅ **Cost Efficient**: Fast rebuilds with optimized Dockerfiles

## Documentation

- **[MICROSERVICES_README.md](MICROSERVICES_README.md)** - Complete deployment guide with exact commands
- **[Copilot Instructions](.github/copilot-instructions.md)** - Architecture details and development patterns

## Processing Pipeline

Audio (MP3/WAV) → Demucs (drum isolation) → AnNOTEator (ML transcription) → MusicXML sheet music

**Typical processing time**: 2-3 minutes for a 4-minute song

## Environment Requirements

**Critical Environment Variables:**
```bash
# Worker Service
DEMUCS_NUM_WORKERS=1                               # Prevents Cloud Run hanging
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python     # TensorFlow compatibility
```

**Resource Configuration:**
- **Worker**: 32GB RAM, 8 CPU, min-instances=1, no CPU throttling
- **API**: 512MB RAM, scales to zero

## Legacy Cleanup Status

❌ **Removed Legacy Components:**
- `backend/` - Monolithic backend (replaced by microservices)
- `crepe/`, `omnizart/` - Unused ML libraries  
- `docker-compose.yml`, `Dockerfile` - Old configurations
- `temp/`, `uploads/`, `logs/` - Temporary directories

✅ **Current Active Components:**
- `api-service/`, `annoteator-worker/` - Microservices
- `library/AnNOTEator/`, `demucs/` - Core ML processing
- `docker-compose.microservices.yml` - Active configuration
- `deploy-scripts/` - Deployment automation

## Support

For detailed setup instructions, troubleshooting, and deployment commands, see [MICROSERVICES_README.md](MICROSERVICES_README.md).