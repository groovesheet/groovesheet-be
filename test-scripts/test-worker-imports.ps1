# Test Worker - Verify imports work
# Quick test to see if the import logging appears

Write-Host "Testing worker imports with diagnostic logging..." -ForegroundColor Cyan
Write-Host ""

$PROJECT_ROOT = "D:\Coding Files\GitHub\groovesheet\groovesheet-be"
cd $PROJECT_ROOT

# Build with cache to speed up
Write-Host "Building worker image..." -ForegroundColor Yellow
docker build --platform=linux/amd64 -f worker-service/Dockerfile -t groovesheet-worker-test .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

# Create a minimal test job
$TEST_JOB_ID = "import-test-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
$TEST_DIR = "$PROJECT_ROOT\shared-jobs\$TEST_JOB_ID"

Write-Host ""
Write-Host "Creating test job: $TEST_JOB_ID" -ForegroundColor Yellow

New-Item -ItemType Directory -Force -Path $TEST_DIR | Out-Null
Copy-Item "$PROJECT_ROOT\Nirvana - Smells Like Teen Spirit.mp3" "$TEST_DIR\input.mp3"

# Create metadata
$metadata = @{
    job_id = $TEST_JOB_ID
    status = "queued"
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    filename = "Nirvana - Smells Like Teen Spirit.mp3"
    progress = 0
} | ConvertTo-Json

$metadata | Out-File -FilePath "$TEST_DIR\metadata.json" -Encoding utf8

Write-Host "✓ Test job created" -ForegroundColor Green
Write-Host ""
Write-Host "Running worker (will stop after first import logs)..." -ForegroundColor Yellow
Write-Host "Watch for 'ENTERED transcribe_audio()' and import logs" -ForegroundColor Gray
Write-Host ""

# Run with timeout - we just want to see the import logs
docker run --rm `
  --platform=linux/amd64 `
  -v "${PROJECT_ROOT}/shared-jobs:/app/shared-jobs" `
  -e "USE_CLOUD_STORAGE=false" `
  -e "LOCAL_JOBS_DIR=/app/shared-jobs" `
  -e "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python" `
  -e "TF_CPP_MIN_LOG_LEVEL=3" `
  --memory=4g `
  --cpus=2 `
  groovesheet-worker-test `
  timeout 30 python -u worker_local.py $TEST_JOB_ID

Write-Host ""
Write-Host "Test complete - check logs above for import diagnostics" -ForegroundColor Cyan
