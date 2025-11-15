#!/usr/bin/env pwsh
# Quick code update - copies Python files into running container
# Use this for Python code changes ONLY (not dependency changes)

$ErrorActionPreference = "Stop"

$PROJECT_ID = "groovesheet2025"
$SERVICE_NAME = "annoteator-worker"
$REGION = "asia-southeast1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Ultra-Fast Code Update (No Rebuild)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This updates Python code WITHOUT rebuilding the Docker image." -ForegroundColor Yellow
Write-Host "Use this for code changes in:" -ForegroundColor Yellow
Write-Host "  - backend/app/services/annoteator_service.py" -ForegroundColor White
Write-Host "  - annoteator-worker/worker.py" -ForegroundColor White
Write-Host ""
Write-Host "DO NOT use this for dependency changes (requirements.txt)" -ForegroundColor Red
Write-Host ""

# Create temp directory with updated code
$TEMP_DIR = New-Item -ItemType Directory -Path (Join-Path $env:TEMP "groovesheet-update-$(Get-Date -Format 'yyyyMMddHHmmss')") -Force
Write-Host "📦 Packaging updated code..." -ForegroundColor Yellow

# Copy files to temp
Copy-Item -Path "backend/app/services/annoteator_service.py" -Destination "$TEMP_DIR/annoteator_service.py"
Copy-Item -Path "annoteator-worker/worker.py" -Destination "$TEMP_DIR/worker.py"

# Create update script
$UPDATE_SCRIPT = @"
#!/bin/bash
set -e
echo "Updating files in container..."
cp /tmp/update/annoteator_service.py /app/backend/app/services/annoteator_service.py
cp /tmp/update/worker.py /app/worker.py
echo "✓ Files updated"
echo "Restarting worker process..."
pkill -f "python.*worker.py" || true
sleep 2
python -u /app/worker.py &
echo "✓ Worker restarted"
"@

Set-Content -Path "$TEMP_DIR/update.sh" -Value $UPDATE_SCRIPT

Write-Host "✓ Code packaged" -ForegroundColor Green
Write-Host ""

# Get running instance
Write-Host "🔍 Finding running container..." -ForegroundColor Yellow
$REVISION = gcloud run revisions list --service=$SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format="value(name)" --limit=1

if (-not $REVISION) {
    Write-Host "✗ No running instances found. Deploy normally first." -ForegroundColor Red
    exit 1
}

Write-Host "✓ Found revision: $REVISION" -ForegroundColor Green
Write-Host ""

# Update via Cloud Run exec
Write-Host "📤 Uploading code to container..." -ForegroundColor Yellow
Write-Host ""

# Note: gcloud run services update with --image will trigger redeploy
# Instead, we'll use a different approach: build minimal layer
Write-Host "⚠️  Cloud Run doesn't support live file updates." -ForegroundColor Yellow
Write-Host "Building minimal Docker layer instead..." -ForegroundColor Cyan
Write-Host ""

# Create minimal Dockerfile
$MINIMAL_DOCKERFILE = @"
FROM gcr.io/groovesheet2025/annoteator-worker:latest
COPY backend/app/services/annoteator_service.py /app/backend/app/services/annoteator_service.py
COPY annoteator-worker/worker.py /app/worker.py
"@

Set-Content -Path "Dockerfile.update" -Value $MINIMAL_DOCKERFILE

Write-Host "🔨 Building tiny update layer (5-10 seconds)..." -ForegroundColor Yellow
docker build --platform=linux/amd64 -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest -f Dockerfile.update .

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Build failed" -ForegroundColor Red
    Remove-Item "Dockerfile.update" -Force
    exit 1
}

Write-Host "✓ Update layer built" -ForegroundColor Green
Write-Host ""

Write-Host "📤 Pushing to GCR..." -ForegroundColor Yellow
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Push failed" -ForegroundColor Red
    Remove-Item "Dockerfile.update" -Force
    exit 1
}

Write-Host "✓ Pushed" -ForegroundColor Green
Write-Host ""

Write-Host "🚀 Deploying updated code..." -ForegroundColor Yellow
gcloud run services update $SERVICE_NAME `
    --region=$REGION `
    --project=$PROJECT_ID

Remove-Item "Dockerfile.update" -Force

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✓ Code Updated Successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "New instances will use the updated code." -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "✗ Deployment failed" -ForegroundColor Red
}
