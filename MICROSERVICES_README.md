# Groovesheet Microservices Architecture

## Why Microservices?

**Problem**: TensorFlow 2.5.0 requires `protobuf==3.9.2`, but modern `google-cloud-storage` requires `protobuf>=3.19.5`. They're incompatible.

**Solution**: Split into two services:
- **API Service**: FastAPI + modern Cloud Storage (no TensorFlow)
- **Worker Service**: TensorFlow + Omnizart + Demucs (no Cloud Storage conflicts)

## Architecture

```
Frontend → API Service → Cloud Storage ← Worker Service
                  ↓
            Pub/Sub Queue
                  ↓
            Worker Service
```

### Flow:
1. Frontend uploads MP3 to API service
2. API saves file to GCS, creates job metadata
3. API publishes message to Pub/Sub topic
4. Worker picks up message, downloads file from GCS
5. Worker processes audio (Demucs → Omnizart)
6. Worker uploads MusicXML to GCS, updates job status
7. Frontend polls API for status, downloads result

## Local Development

### Prerequisites
- Docker & Docker Compose
- GCP Service Account credentials (`credentials.json`)

### Run Locally
```bash
docker-compose -f docker-compose.microservices.yml up --build
```

This starts:
- API on http://localhost:8080
- Worker (background)
- Pub/Sub emulator (for local messaging)

## Cloud Deployment

### Setup Pub/Sub
```bash
# Create topic
gcloud pubsub topics create groovesheet-worker-tasks

# Create subscription
gcloud pubsub subscriptions create groovesheet-worker-tasks-sub \
  --topic=groovesheet-worker-tasks
```

### Deploy API Service
```bash
cd api-service
gcloud run deploy groovesheet-api \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars GCS_BUCKET_NAME=groovesheet-jobs,GCP_PROJECT=groovesheet2025
```

### Deploy Worker Service
```bash
cd worker-service
gcloud run deploy groovesheet-worker \
  --source . \
  --region asia-southeast1 \
  --no-allow-unauthenticated \
  --set-env-vars GCS_BUCKET_NAME=groovesheet-jobs,GCP_PROJECT=groovesheet2025 \
  --memory 4Gi \
  --cpu 2 \
  --timeout 600
```

## Benefits

✅ **No dependency conflicts** - Each service has its own environment
✅ **Independent scaling** - Scale API and workers separately
✅ **Better reliability** - API stays fast, workers can retry
✅ **Easier debugging** - Separate logs for each service
✅ **Cost efficient** - Workers only run when processing jobs

## Migration from Monolith

Your existing code mostly stays the same:
- `backend/app/services/audio_processor.py` → Used by worker
- `backend/app/api/routes/transcription.py` → Replaced by `api-service/main.py`
- Frontend changes minimal → Same API endpoints, same flow
