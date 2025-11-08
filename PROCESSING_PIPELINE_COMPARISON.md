# Processing Pipeline Comparison: Monolith vs Worker

## Original Monolithic Backend Flow

### Endpoint: `/api/annoteator/upload`
```python
# 1. Receive upload
file: UploadFile
song_title: str = Form(default="Drum Transcription")

# 2. Save to temp location
temp_audio = upload_dir / f"upload_{session_id}{file_ext}"
with open(temp_audio, "wb") as f:
    f.write(await file.read())

# 3. Call AnNOTEatorService
musicxml_path, metadata = annoteator_service.transcribe_audio(
    audio_path=str(temp_audio),
    output_name=f"transcription_{session_id}",
    song_title=song_title
)

# 4. Return response
return TranscriptionResponse(
    success=True,
    musicxml_path=musicxml_path,
    metadata=metadata,
    download_url=f"/api/annoteator/download/{session_id}"
)
```

### Service Configuration
```python
# settings.py
UPLOAD_DIR: str = "./uploads"
TEMP_DIR: str = "./temp"
OUTPUT_DIR: str = "./outputs"
LOG_LEVEL: str = "INFO"

# AnNOTEatorService init
annoteator_service = AnNOTEatorService(output_dir=settings.OUTPUT_DIR)
```

---

## Worker Service Flow

### Job Polling
```python
# 1. Poll for jobs
job_dirs = glob.glob(os.path.join(LOCAL_JOBS_DIR, "*"))

# 2. Read job metadata
metadata_path = os.path.join(job_dir, "metadata.json")
input_path = os.path.join(job_dir, "input.mp3")
output_path = os.path.join(job_dir, "output.musicxml")

# 3. Call AnNOTEatorService
annoteator = AnNOTEatorService(output_dir=job_dir)
result_path, result_metadata = annoteator.transcribe_audio(
    audio_path=input_path,
    output_name="output",
    song_title=metadata.get('filename', 'Drum Transcription'),
    use_demucs=True
)

# 4. Copy result
shutil.copy(result_path, output_path)

# 5. Update metadata
metadata['status'] = 'completed'
metadata['progress'] = 100
```

### Service Configuration
```python
# Environment
LOCAL_JOBS_DIR: str = "/app/jobs"

# AnNOTEatorService init
annoteator = AnNOTEatorService(output_dir=job_dir)
```

---

## Critical Comparison

| Aspect | Monolith Backend | Worker Service | ✅ Status |
|--------|------------------|----------------|-----------|
| **Service Class** | `AnNOTEatorService` | `AnNOTEatorService` | ✅ Same |
| **Method Called** | `transcribe_audio()` | `transcribe_audio()` | ✅ Same |
| **use_demucs** | Default `True` | Explicit `True` | ✅ Same |
| **Output Directory** | `settings.OUTPUT_DIR` | `job_dir` | ⚠️ Different |
| **Output Filename** | `transcription_{session_id}` | `output` | ⚠️ Different |
| **Song Title** | From form data | From metadata | ✅ Same source |
| **Input Path** | Temp upload file | `input.mp3` | ✅ Different but OK |
| **Return Handling** | Direct response | Copy to output.musicxml | ✅ Different but OK |
| **Logging** | FastAPI logging | Worker logging | ⚠️ Need to verify |
| **PYTHONPATH** | `/app/backend:/app/AnNOTEator:/app/demucs` | Same | ✅ Same |
| **Environment Vars** | Multiple | Multiple | ⚠️ Need to verify |

---

## Key Differences (By Design)

### 1. Output Directory Handling
**Monolith:**
```python
annoteator_service = AnNOTEatorService(output_dir=settings.OUTPUT_DIR)
# All outputs go to: ./outputs/transcription_{session_id}.musicxml
```

**Worker:**
```python
annoteator = AnNOTEatorService(output_dir=job_dir)
# Outputs go to: /app/jobs/{job_id}/output.musicxml
```

✅ **This is intentional** - Worker needs outputs in the job directory for easy retrieval.

### 2. Logging Configuration
**Monolith:**
```python
# backend/app/core/logging_config.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console
        RotatingFileHandler()      # File
    ]
)
```

**Worker:**
```python
# worker_local.py
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

⚠️ **ISSUE FOUND:** Worker has simpler logging - no format specified!

---

## Environment Variables Comparison

### Monolith Docker Compose
```yaml
environment:
  - HOST=0.0.0.0
  - PORT=8000
  - DEBUG=false
  - DEMUCS_DEVICE=cpu
  - OMNIZART_DEVICE=cpu
  - MAX_CONCURRENT_JOBS=2
  - LOG_LEVEL=INFO
  - PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

### Worker Docker Compose
```yaml
environment:
  - USE_CLOUD_STORAGE=false
  - LOCAL_JOBS_DIR=/app/jobs
  - PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

⚠️ **MISSING:** Worker doesn't have `DEMUCS_DEVICE`, `LOG_LEVEL` settings!

---

## Issues Found

### 1. ❌ Logging Format Not Identical
**Problem:** Worker uses basic logging, monolith uses formatted logging

**Fix:**
```python
# worker_local.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 2. ❌ Missing Environment Variables
**Problem:** Worker doesn't set `LOG_LEVEL`, `DEMUCS_DEVICE`

**Fix in docker-compose.local.yml:**
```yaml
environment:
  - USE_CLOUD_STORAGE=false
  - LOCAL_JOBS_DIR=/app/jobs
  - PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
  - LOG_LEVEL=INFO
  - DEMUCS_DEVICE=cpu
```

### 3. ⚠️ Stdout Buffering in Docker
**Problem:** Python output may be buffered in Docker containers

**Already Fixed:** Worker Dockerfile has:
```dockerfile
ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "worker.py"]
```
✅ This is correct!

---

## Processing Pipeline (Core Logic)

Both use **EXACT SAME** `AnNOTEatorService.transcribe_audio()`:

```python
def transcribe_audio(audio_path, output_name, song_title, use_demucs=True):
    # STEP 1: Demucs drum extraction (if enabled)
    if use_demucs:
        drum_track, sample_rate = drum_extraction(audio_path, ...)
    
    # STEP 2: Convert to frames
    df, bpm = drum_to_frame(drum_track, sample_rate)
    
    # STEP 3: Predict drum hits (TensorFlow)
    prediction_df = predict_drumhit(model_path, df, sample_rate)
    
    # STEP 4: Generate MusicXML
    sheet_music = drum_transcriber(prediction_df, duration, bpm, ...)
    sheet_music.sheet.write(fp=output_musicxml)
    
    return output_musicxml, metadata
```

✅ **No differences in core processing!**

---

## Fixes Required

### 1. Update Worker Logging
```python
# worker_local.py - Line 12
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 2. Add Missing Environment Variables
```yaml
# docker-compose.local.yml
environment:
  - LOG_LEVEL=INFO
  - DEMUCS_DEVICE=cpu
```

### 3. Verify PYTHONPATH (Already Correct)
```dockerfile
ENV PYTHONPATH=/app:/app/backend:/app/AnNOTEator:/app/demucs:$PYTHONPATH
```

---

## Summary

✅ **Core processing is IDENTICAL** - both use same `AnNOTEatorService`  
✅ **Demucs settings are SAME** - both use performance mode  
✅ **TensorFlow model is SAME** - complete_network.h5  
⚠️ **Logging needs standardization** - format string missing  
⚠️ **Environment variables incomplete** - add LOG_LEVEL, DEMUCS_DEVICE  

Once these fixes are applied, worker will behave **exactly** like the monolith backend!
