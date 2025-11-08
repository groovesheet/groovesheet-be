# GrooveSheet Architecture Comparison

## Original Monolithic Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Single Container                         │
│                  (drumscore-backend)                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              FastAPI Backend                         │  │
│  │  - Upload endpoints                                  │  │
│  │  - Health checks                                     │  │
│  │  - Job management                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Audio Processing Services                    │  │
│  │  - AnNOTEatorService                                 │  │
│  │  - TensorFlow 2.5.0                                  │  │
│  │  - Demucs (drum extraction)                          │  │
│  │  - MusicXML generation                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Google Cloud Storage                      │  │
│  │  (google-cloud-storage 1.42.3)                      │  │
│  │  (protobuf 3.9.2 - compatible with TF 2.5.0)        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Resources:                                                 │
│  - Memory: 4GB-8GB                                          │
│  - CPU: 2-4 cores                                           │
│  - Platform: linux/amd64                                    │
│  - ENV: PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         │
         │ HTTP
         ▼
    Frontend (React)
```

### Pros ✅
- **Simple deployment** - One container to manage
- **No network overhead** - Direct function calls
- **Easy debugging** - All logs in one place
- **No dependency conflicts** - Everything uses protobuf 3.9.2

### Cons ❌
- **Resource waste** - Container runs even when idle
- **Tight coupling** - Can't scale API and processing separately
- **Slow responses** - API blocks during processing
- **Single point of failure** - Crash affects everything

---

## New Microservices Architecture

```
┌──────────────────────────┐         ┌─────────────────────────┐
│     API Container        │         │    Worker Container     │
│  (groovesheet-api)       │         │  (groovesheet-worker)   │
├──────────────────────────┤         ├─────────────────────────┤
│                          │         │                         │
│  FastAPI (Lightweight)   │         │  AnNOTEatorService      │
│  - Upload endpoints      │         │  - TensorFlow 2.5.0     │
│  - Job status            │         │  - Demucs               │
│  - Health checks         │         │  - Protobuf 3.9.2       │
│                          │         │                         │
│  Dependencies:           │         │  Dependencies:          │
│  ✓ google-cloud-storage  │         │  ✓ TensorFlow 2.5.0     │
│    (modern, ≥3.19.5)     │         │  ✓ protobuf 3.9.2       │
│  ✓ protobuf ≥3.19.5      │         │  ✓ librosa, madmom      │
│  ✗ NO TensorFlow         │         │  ✗ NO google-cloud-*    │
│                          │         │    (deps only)          │
│  Resources:              │         │                         │
│  - Memory: 512MB-1GB     │         │  Resources:             │
│  - CPU: 0.5-1 core       │         │  - Memory: 4GB-8GB ⚠️   │
│  - Always running        │         │  - CPU: 2-4 cores       │
│                          │         │  - Runs on demand       │
└──────────────────────────┘         └─────────────────────────┘
         │                                       ▲
         │ Publishes job                         │ Subscribes
         │ to Pub/Sub                            │ to topic
         ▼                                       │
┌──────────────────────────────────────────────────────────────┐
│                   Google Cloud Pub/Sub                       │
│              (or local emulator for dev)                     │
│                                                              │
│  Topic: groovesheet-worker-tasks                            │
│  Subscription: groovesheet-worker-tasks-sub                 │
└──────────────────────────────────────────────────────────────┘
         │
         │ Both read/write
         ▼
┌──────────────────────────────────────────────────────────────┐
│              Google Cloud Storage (GCS)                      │
│                  or Local Filesystem                         │
│                                                              │
│  Buckets/Directories:                                       │
│  - groovesheet-jobs/ (or ./shared-jobs/)                    │
│    - {job_id}/                                              │
│      - input.mp3                                            │
│      - metadata.json                                        │
│      - output.musicxml                                      │
└──────────────────────────────────────────────────────────────┘
         ▲
         │
         │ Polls for results
         │
    Frontend (React)
```

### Pros ✅
- **Solves dependency conflicts** - TensorFlow and GCS in separate containers
- **Independent scaling** - Scale workers based on queue depth
- **Better resource usage** - Workers can scale to zero
- **Non-blocking API** - Fast responses, processing happens async
- **Fault isolation** - Worker crash doesn't affect API

### Cons ❌
- **More complex** - Two services, Pub/Sub, GCS
- **Network overhead** - Communication through Pub/Sub/GCS
- **Harder debugging** - Logs split across containers
- **Local dev complexity** - Need emulators or shared volumes

---

## Key Differences

| Aspect | Monolith | Microservices |
|--------|----------|---------------|
| **Containers** | 1 | 2+ (API + Workers) |
| **Deployment** | Single docker-compose | Multiple services |
| **Dependencies** | All in one | Split: API vs Processing |
| **Protobuf** | 3.9.2 everywhere | 3.9.2 (worker) vs ≥3.19.5 (API) |
| **Communication** | Direct function calls | Pub/Sub + GCS |
| **Response Time** | Slow (blocking) | Fast (async) |
| **Resource Usage** | Always 4-8GB | API: 512MB, Worker: 4-8GB |
| **Scaling** | Vertical only | Horizontal workers |
| **Debugging** | Easier | Harder |

---

## Critical Setup Differences

### Monolith Dockerfile (Working)
```dockerfile
# Full installation steps
RUN pip install 'tensorflow==2.5.0' 'protobuf==3.9.2'
RUN pip install 'typing-extensions>=4.8.0'
RUN cd /app/demucs && pip install -e .
RUN cd /app/omnizart && pip install -e .

# CRITICAL fixes
RUN pip install --force-reinstall 'protobuf==3.9.2'
RUN pip install --upgrade --force-reinstall 'typing-extensions>=4.8.0'

# Environment setup
ENV PYTHONPATH=/app:/app/backend:/app/AnNOTEator:/app/demucs:/app/omnizart:$PYTHONPATH
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

### Worker Dockerfile (Broken) ❌
```dockerfile
# Missing steps:
# ✗ No omnizart installation
# ✗ No typing-extensions fix
# ✗ No protobuf re-install after omnizart
# ✗ No PYTHONPATH setup
# ✗ No PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION
```

---

## The Problem: Exit Code 139 (Segmentation Fault)

The worker crashes with exit code 139 (SIGSEGV) because:

1. **Missing PYTHONPATH** - Python can't find modules properly
2. **Wrong protobuf version** - Gets overwritten by omnizart install
3. **Missing typing-extensions** - TensorFlow compatibility issue
4. **No PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION** - Runtime protobuf conflict

The worker Dockerfile is **incomplete** compared to the working monolith Dockerfile!

---

## Recommended Fix

Update `worker-service/Dockerfile` to match the working setup from the monolith:

```dockerfile
# After installing requirements:
RUN cd /app/omnizart && pip install -e . || echo "Omnizart already available"

# CRITICAL: Re-fix protobuf after omnizart
RUN pip install --force-reinstall 'protobuf==3.9.2'

# CRITICAL: Re-upgrade typing-extensions
RUN pip install --upgrade --force-reinstall 'typing-extensions>=4.8.0'

# Set PYTHONPATH
ENV PYTHONPATH=/app:/app/backend:/app/AnNOTEator:/app/demucs:/app/omnizart:$PYTHONPATH

# Set protobuf implementation (also in docker-compose)
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

And ensure `docker-compose.local.yml` has memory limits:
```yaml
deploy:
  resources:
    limits:
      memory: 8G
```
