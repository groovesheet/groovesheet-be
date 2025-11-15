# Demucs Worker Service

A microservice for audio source separation using Demucs. This worker handles drum extraction and full source separation (drums, bass, vocals, other) from audio files.

## Structure

```
demucs-worker/
├── worker.py                 # Main worker entrypoint (cloud/local pub/sub)
├── services/
│   ├── __init__.py
│   └── demucs_service.py     # Demucs processing service
├── Dockerfile                # Container definition
├── cloudbuild.yaml           # GCP Cloud Build configuration
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Configuration

Create a `.env` file in the `demucs-worker/` directory with the following variables:

```bash
# Cloud/Local Mode
USE_CLOUD_STORAGE=true

# GCP Configuration (for cloud mode)
GCP_PROJECT=groovesheet2025
DEMUCS_WORKER_SUBSCRIPTION=groovesheet-demucs-worker-tasks-sub
GCS_BUCKET_NAME=groovesheet-jobs

# Local Configuration (for local mode)
LOCAL_JOBS_DIR=/app/testing/local-jobs

# Server Configuration
PORT=8081

# Demucs Processing Configuration
DEMUCS_DEVICE=cpu
DEMUCS_NUM_WORKERS=1
DEMUCS_MODE=speed
DEMUCS_MODEL_DIR=

# Performance Configuration
OMP_NUM_THREADS=4

# Logging
LOG_LEVEL=INFO
```

### Environment Variables Explained

- **USE_CLOUD_STORAGE**: `true` for GCP Cloud Run, `false` for local development
- **DEMUCS_WORKER_SUBSCRIPTION**: Pub/Sub subscription name for cloud mode
- **DEMUCS_DEVICE**: Device to use (`cpu` or `cuda` for GPU)
- **DEMUCS_NUM_WORKERS**: Number of worker processes (set to `1` for Cloud Run to prevent hanging)
- **DEMUCS_MODE**: `speed` (single model, faster) or `performance` (4 models, better quality)
- **DEMUCS_MODEL_DIR**: Optional path to custom model directory (defaults to AnNOTEator's models if available)

## Usage

### Cloud Mode (GCP Cloud Run)

1. **Build and deploy:**
   ```bash
   gcloud builds submit --config=demucs-worker/cloudbuild.yaml
   gcloud run deploy demucs-worker \
     --image gcr.io/groovesheet2025/demucs-worker \
     --platform managed \
     --region us-central1 \
     --memory 16Gi \
     --cpu 4 \
     --timeout 3600 \
     --set-env-vars "USE_CLOUD_STORAGE=true,GCP_PROJECT=groovesheet2025,DEMUCS_WORKER_SUBSCRIPTION=groovesheet-demucs-worker-tasks-sub,DEMUCS_DEVICE=cpu,DEMUCS_NUM_WORKERS=1,DEMUCS_MODE=speed,LOG_LEVEL=INFO"
   ```

2. **Publish a job message to Pub/Sub:**
   ```python
   from google.cloud import pubsub_v1
   import json
   
   publisher = pubsub_v1.PublisherClient()
   topic_path = publisher.topic_path("groovesheet2025", "groovesheet-demucs-worker-tasks")
   
   message = {
       "job_id": "your-job-id",
       "bucket": "groovesheet-jobs"
   }
   publisher.publish(topic_path, json.dumps(message).encode("utf-8"))
   ```

3. **Job structure in GCS:**
   ```
   gs://groovesheet-jobs/jobs/{job_id}/
   ├── input.mp3          # Input audio file
   ├── metadata.json      # Job metadata
   └── drums.wav          # Output (created by worker)
   ```

### Local Mode

1. **Set environment variables:**
   ```bash
   export USE_CLOUD_STORAGE=false
   export LOCAL_JOBS_DIR=/path/to/local-jobs
   ```

2. **Run the worker:**
   ```bash
   cd demucs-worker
   python worker.py
   ```

3. **Job structure in local filesystem:**
   ```
   /path/to/local-jobs/{job_id}/
   ├── input.mp3          # Input audio file
   ├── metadata.json      # Job metadata
   └── drums.wav          # Output (created by worker)
   ```

### Metadata Format

The `metadata.json` file should contain:

```json
{
  "filename": "Song Name",
  "extract_drums_only": true,
  "status": "pending",
  "progress": 0
}
```

- **extract_drums_only**: `true` to extract only drums, `false` to extract all sources (drums, bass, vocals, other)
- **status**: Job status (`pending`, `processing`, `completed`, `failed`)
- **progress**: Progress percentage (0-100)

## Testing

### Local Testing

1. **Create a test job directory:**
   ```bash
   mkdir -p testing/local-jobs/test-job-123
   ```

2. **Add input file and metadata:**
   ```bash
   cp your-audio.mp3 testing/local-jobs/test-job-123/input.mp3
   cat > testing/local-jobs/test-job-123/metadata.json << EOF
   {
     "filename": "Test Song",
     "extract_drums_only": true,
     "status": "pending",
     "progress": 0
   }
   EOF
   ```

3. **Run the worker:**
   ```bash
   cd demucs-worker
   USE_CLOUD_STORAGE=false LOCAL_JOBS_DIR=../testing/local-jobs python worker.py
   ```

4. **Check output:**
   ```bash
   ls -lh testing/local-jobs/test-job-123/
   # Should see: drums.wav, metadata.json (updated), input.mp3
   ```

### Docker Testing

1. **Build the image:**
   ```bash
   docker build -t demucs-worker -f demucs-worker/Dockerfile .
   ```

2. **Run locally:**
   ```bash
   docker run -it --rm \
     -e USE_CLOUD_STORAGE=false \
     -e LOCAL_JOBS_DIR=/app/jobs \
     -v $(pwd)/testing/local-jobs:/app/jobs \
     demucs-worker
   ```

### Integration Testing

Test the service directly:

```python
from services.demucs_service import DemucsService

# Initialize service
service = DemucsService(output_dir="./test_output")

# Separate audio
output_path, metadata = service.separate_audio(
    audio_path="test_audio.mp3",
    extract_drums_only=True
)

print(f"Output: {output_path}")
print(f"Metadata: {metadata}")
```

## Architecture

The demucs-worker follows the same architecture pattern as `annoteator-worker`:

1. **Worker (`worker.py`)**: Handles pub/sub subscription (cloud) or filesystem polling (local)
2. **Service (`services/demucs_service.py`)**: Contains the actual Demucs processing logic
3. **Cloud/Local Modes**: Supports both GCP Cloud Run and local development

### Processing Flow

1. Worker receives job (via Pub/Sub or filesystem)
2. Downloads/loads input audio file
3. Calls `DemucsService.separate_audio()`
4. Demucs separates audio into sources
5. Saves output (drums.wav or all sources)
6. Updates metadata.json with results
7. Uploads results (cloud mode) or saves locally

## Dependencies

- **demucs==3.0.4**: Audio source separation library
- **torch==1.13.1**: PyTorch for Demucs models
- **librosa**: Audio processing
- **google-cloud-storage/pubsub**: GCP integration
- **soundfile**: Audio I/O

## Notes

- **Model Files**: Demucs models are stored in `library/AnNOTEator/inference/pretrained_models/demucs/` (shared with AnNOTEator)
- **Performance**: `speed` mode uses 1 model (~1-2 min), `performance` mode uses 4 models (~4-6 min)
- **Memory**: Requires 4-8GB RAM for speed mode, 16GB+ for performance mode
- **Workers**: Set `DEMUCS_NUM_WORKERS=1` in Cloud Run to prevent hanging


