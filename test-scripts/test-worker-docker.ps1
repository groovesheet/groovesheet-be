# Test Worker in Docker Locally
# This tests using the actual Docker container (same as production)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Testing Worker in Docker" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$PROJECT_ROOT = "D:\Coding Files\GitHub\groovesheet\groovesheet-be"
Set-Location $PROJECT_ROOT

Write-Host "Step 1: Building worker Docker image..." -ForegroundColor Yellow
Write-Host "This may take 5-10 minutes on first build..." -ForegroundColor Gray
Write-Host ""

# Build the worker image
docker build -t groovesheet-worker-test -f worker-service/Dockerfile --platform=linux/amd64 . 2>&1 | ForEach-Object {
    if ($_ -match "^Step \d+/\d+") {
        Write-Host $_ -ForegroundColor Cyan
    } elseif ($_ -match "ERROR|error") {
        Write-Host $_ -ForegroundColor Red
    } else {
        Write-Host $_ -ForegroundColor Gray
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Docker build failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ Docker image built successfully" -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Creating test job..." -ForegroundColor Yellow
Write-Host ""

# Create a test job directory
$TEST_JOB_ID = "docker-test-" + (Get-Date -Format "yyyyMMdd-HHmmss")
$TEST_JOB_DIR = Join-Path (Join-Path $PROJECT_ROOT "shared-jobs") $TEST_JOB_ID
New-Item -ItemType Directory -Path $TEST_JOB_DIR -Force | Out-Null

# Copy test audio
$TEST_AUDIO = Join-Path $PROJECT_ROOT "Nirvana - Smells Like Teen Spirit (Official Music Video).mp3"
if (!(Test-Path $TEST_AUDIO)) {
    Write-Host "❌ Test audio not found: $TEST_AUDIO" -ForegroundColor Red
    Write-Host "Please place a test MP3 file in the project root" -ForegroundColor Yellow
    exit 1
}

Copy-Item $TEST_AUDIO -Destination (Join-Path $TEST_JOB_DIR "input.mp3")

# Create metadata
$METADATA = @{
    job_id = $TEST_JOB_ID
    status = "queued"
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    filename = "Nirvana - Smells Like Teen Spirit.mp3"
    progress = 0
} | ConvertTo-Json

Set-Content -Path (Join-Path $TEST_JOB_DIR "metadata.json") -Value $METADATA

Write-Host "✓ Test job created: $TEST_JOB_ID" -ForegroundColor Green
Write-Host "  Location: $TEST_JOB_DIR" -ForegroundColor Gray
Write-Host ""

Write-Host "Step 3: Running worker in Docker..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "This will process the full audio file and may take 5-10 minutes" -ForegroundColor Gray
Write-Host "Watch for detailed logs showing each processing step..." -ForegroundColor Gray
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""

# Run worker with local test script
$containerStartTime = Get-Date

Write-Host "Container resources:" -ForegroundColor Cyan
Write-Host "  Memory: 32GB (maximum available)" -ForegroundColor White
Write-Host "  CPU: 4 cores (all available)" -ForegroundColor White
Write-Host ""

docker run --rm `
  --platform=linux/amd64 `
  -v "${PROJECT_ROOT}/shared-jobs:/app/shared-jobs" `
  -e "USE_CLOUD_STORAGE=false" `
  -e "LOCAL_JOBS_DIR=/app/shared-jobs" `
  -e "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python" `
  -e "TF_CPP_MIN_LOG_LEVEL=3" `
  -e "DEMUCS_DEVICE=cpu" `
  -e "OMP_NUM_THREADS=4" `
  --memory=32g `
  --memory-swap=32g `
  --cpus=4 `
  --shm-size=8g `
  groovesheet-worker-test `
  python -u worker_local.py $TEST_JOB_ID

$exitCode = $LASTEXITCODE
$containerEndTime = Get-Date
$duration = $containerEndTime - $containerStartTime

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Container exit code: $exitCode" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } elseif ($exitCode -eq 137) { "Red" } else { "Yellow" })
if ($exitCode -eq 137) {
    Write-Host "Exit code 137 = Container killed by Docker (likely OUT OF MEMORY)" -ForegroundColor Red
    Write-Host "Try increasing --memory allocation or reducing CPU workers" -ForegroundColor Yellow
} elseif ($exitCode -eq 139) {
    Write-Host "Exit code 139 = Segmentation fault" -ForegroundColor Red
}
Write-Host ""

if ($exitCode -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✓ Worker Test PASSED" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Processing time: $($duration.TotalMinutes.ToString('F1')) minutes" -ForegroundColor White
    Write-Host "Check output in: $TEST_JOB_DIR" -ForegroundColor White
    Write-Host ""
    
    # Check for output file
    $OUTPUT_FILE = Join-Path $TEST_JOB_DIR "output.musicxml"
    if (Test-Path $OUTPUT_FILE) {
        $fileSize = (Get-Item $OUTPUT_FILE).Length / 1KB
        Write-Host "✓ Output file created: output.musicxml ($($fileSize.ToString('F1')) KB)" -ForegroundColor Green
    } else {
        Write-Host "⚠️  No output file found" -ForegroundColor Yellow
    }
    
    # Show metadata
    $METADATA_FILE = Join-Path $TEST_JOB_DIR "metadata.json"
    if (Test-Path $METADATA_FILE) {
        Write-Host ""
        Write-Host "Final job metadata:" -ForegroundColor Cyan
        Get-Content $METADATA_FILE | ConvertFrom-Json | Format-List
    }
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  ❌ Worker Test FAILED" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Processing time: $($duration.TotalMinutes.ToString('F1')) minutes" -ForegroundColor White
    Write-Host "Review the error messages above" -ForegroundColor White
    Write-Host ""
    Write-Host "Troubleshooting tips:" -ForegroundColor Yellow
    Write-Host "  1. Check if all dependencies are installed" -ForegroundColor Gray
    Write-Host "  2. Verify the audio file is valid" -ForegroundColor Gray
    Write-Host "  3. Look for import errors or missing packages" -ForegroundColor Gray
}

Write-Host ""
