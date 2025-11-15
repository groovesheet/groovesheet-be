# Test Scripts

## Overview

This directory contains test scripts for the Groovesheet microservices architecture.

## Key Architectural Changes (New System)

Your friend made the following changes to restructure the system:

### 1. **Service Renaming**
- **Old**: `groovesheet-worker` 
- **New**: `annoteator-worker` (more descriptive)
- Container name: `groovesheet-be-annoteator-worker`

### 2. **Local Storage Path Changes**
- **Old**: `shared-jobs/` directory
- **New**: `testing/local-jobs/` directory
- Better organization for local testing vs production

### 3. **Pub/Sub Emulator Added**
- **New service**: `pubsub-emulator` using Google Cloud SDK
- Runs on port 8085
- Enables proper local testing without GCP credentials
- Both API and Worker now connect to the emulator in local mode

### 4. **Environment Variable Improvements**
- `USE_CLOUD_STORAGE=false` - Properly switches to local file storage
- `LOCAL_JOBS_DIR=/app/jobs` - Configurable job storage location
- Better separation between cloud and local modes

### 5. **Code Structure**
- Worker service logic moved to `annoteator-worker/services/annoteator_service.py`
- Cleaner separation of concerns
- Better error handling and logging

## Available Test Scripts

### `new-system-test.ps1` (RECOMMENDED - Updated for New Architecture)

Tests the NEW microservices architecture with:
- API service
- AnNOTEator worker service  
- Pub/Sub emulator
- Local file storage

**Usage:**
```powershell
# Use default test file (testmusic.mp3 in project root)
.\new-system-test.ps1

# Or specify a custom MP3 file
.\new-system-test.ps1 -TestMp3 "D:\path\to\your\audio.mp3"
```

**What it tests:**
1. Starts all microservices via docker-compose
2. Waits for services to be ready
3. Submits a transcription job
4. Monitors progress in real-time
5. Downloads the resulting MusicXML file
6. Shows logs for debugging
7. Validates the entire pipeline

### `test-full-system.ps1` (OLD - From Master Branch)

This was the original test script from the master branch. It works with the old architecture but references:
- `shared-jobs/` directory (old path)
- Different service names
- No Pub/Sub emulator

**Kept for reference** - Use `new-system-test.ps1` instead.

## What the Test Does

1. **Cleanup**: Removes old job data from previous tests
2. **Start Services**: Launches API, Worker, and Pub/Sub emulator
3. **Health Check**: Waits for API to be ready (up to 45 seconds)
4. **Upload**: Submits an MP3 file to the API
5. **Monitor**: Polls job status every 5 seconds showing progress
6. **Download**: Retrieves the generated MusicXML file
7. **Logs**: Displays service logs for debugging

## Troubleshooting

### Docker Compose Messages Are Normal

You may see messages like:
```
Network groovesheet-be_default  Creating
Container groovesheet-be-pubsub-emulator-1  Creating
```

These are **normal progress messages**, not errors. The test script now filters and displays them properly.

### Common Issues

**API not ready after 45 seconds:**
- Check Docker Desktop is running
- Verify ports 8080 and 8085 are not in use
- Check API logs: `docker-compose -f docker-compose.local.yml logs api`

**Worker not processing jobs:**
- Check worker logs: `docker-compose -f docker-compose.local.yml logs annoteator-worker`
- Verify Pub/Sub emulator is running: `docker-compose -f docker-compose.local.yml ps`
- Ensure `testing/local-jobs/` directory exists

**Job stuck at low progress:**
- Worker may be loading ML models (takes 30-60 seconds first time)
- Check worker logs for errors
- Verify sufficient RAM (32GB recommended for worker)

### Manual Debugging Commands

```powershell
# Check all running containers
docker-compose -f docker-compose.local.yml ps

# View API logs
docker-compose -f docker-compose.local.yml logs -f api

# View worker logs
docker-compose -f docker-compose.local.yml logs -f annoteator-worker

# View Pub/Sub emulator logs
docker-compose -f docker-compose.local.yml logs -f pubsub-emulator

# Check local jobs directory
Get-ChildItem ".\testing\local-jobs"

# Stop all services
docker-compose -f docker-compose.local.yml down

# Rebuild and restart
docker-compose -f docker-compose.local.yml up --build
```

## Expected Output

```
========================================
  Testing Full Microservices System
========================================

🎵 Test file: testmusic.mp3
📁 Size: 1.42 MB

Step 1: Starting microservices system (LOCAL MODE)...
Stopping any existing containers...
Cleaning previous local jobs...
Building and starting services...
  Creating network groovesheet-be_default
  Creating groovesheet-be-pubsub-emulator-1
  Creating groovesheet-be-api-1
  Creating groovesheet-be-annoteator-worker-1
✅ Services started: groovesheet-be-api-1, groovesheet-be-annoteator-worker-1, groovesheet-be-pubsub-emulator-1

Step 2: Waiting for services to be ready...
Checking API health...
✅ API service is ready
Checking worker status...
  Worker container: Up 5 seconds
✅ All services ready

Step 3: Submitting transcription job...
✅ Job submitted successfully
  Job ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890

Step 4: Monitoring job progress...
This may take 2-3 minutes for the full transcription

  [0.1 min] Status: queued | Progress: 0%
  [0.3 min] Status: processing | Progress: 30%
  [0.8 min] Status: processing | Progress: 55%
  [1.5 min] Status: processing | Progress: 80%
  [2.1 min] Status: processing | Progress: 95%

✅ Transcription completed successfully!
  Total time: 2.3 minutes
  Final progress: 100%
  Download URL: /api/v1/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890

Step 6: Testing download...
✅ Download successful
  File: D:\Coding Files\GitHub\groovesheet\groovesheet-be\test_output_20251115_143022.musicxml
  Size: 45.2 KB

========================================
  ✅ FULL SYSTEM TEST PASSED
  All microservices working correctly!
========================================

Stop containers? (y/n):
```

## Next Steps

After a successful test:
1. Your local system is confirmed working
2. You can deploy to GCP using scripts in `deploy-scripts/`
3. Follow `GCP_MIGRATION_INSTRUCTIONS.md` for cloud deployment

## Questions?

- Check `MICROSERVICES_README.md` for architecture details
- Review `GCP_MIGRATION_INSTRUCTIONS.md` for cloud deployment
- Examine service code in `api-service/` and `annoteator-worker/`
