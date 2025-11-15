#!/usr/bin/env pwsh
# Ultra-fast deployment using optimized Dockerfile with better layer caching
# Code changes rebuild in ~5 seconds instead of ~5 minutes

$ErrorActionPreference = "Stop"

$PROJECT_ID = "groovesheet2025"
$REGION = "asia-southeast1"
$WORKER_IMAGE = "gcr.io/$PROJECT_ID/annoteator-worker"
$TAG = "latest"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fast Worker Deploy (Optimized Build)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Using optimized Dockerfile with code copied LAST" -ForegroundColor Yellow
Write-Host "Code-only changes rebuild in ~5 seconds!" -ForegroundColor Green
Write-Host ""

Write-Host "Step 1: Building with optimized Dockerfile..." -ForegroundColor Yellow
Write-Host ""

docker build `
    --platform=linux/amd64 `
    -t "${WORKER_IMAGE}:${TAG}" `
    -f annoteator-worker/Dockerfile.fast `
    .

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ Build failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ Build complete" -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Pushing to GCR..." -ForegroundColor Yellow
Write-Host ""

docker push "${WORKER_IMAGE}:${TAG}"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ Push failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ Image pushed" -ForegroundColor Green
Write-Host ""

Write-Host "Step 3: Deploying to Cloud Run..." -ForegroundColor Yellow
Write-Host ""
Write-Host "⚙️  Configuration:" -ForegroundColor Cyan
Write-Host "   Image: ${WORKER_IMAGE}:${TAG}" -ForegroundColor White
Write-Host "   Memory: 32GB" -ForegroundColor White
Write-Host "   CPU: 8 cores" -ForegroundColor White
Write-Host ""

gcloud run deploy annoteator-worker `
  --image "${WORKER_IMAGE}:${TAG}" `
  --platform managed `
  --region $REGION `
  --memory 32Gi `
  --cpu 8 `
    --no-cpu-throttling `
  --timeout 3600 `
  --concurrency 1 `
  --min-instances 0 `
  --max-instances 3 `
  --no-allow-unauthenticated `
    --set-env-vars "USE_CLOUD_STORAGE=true,GCS_BUCKET_NAME=groovesheet-jobs,WORKER_SUBSCRIPTION=groovesheet-worker-tasks-sub,GCP_PROJECT=$PROJECT_ID,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,LOG_LEVEL=INFO,DEMUCS_DEVICE=cpu,TF_CPP_MIN_LOG_LEVEL=3,OMP_NUM_THREADS=4,DEMUCS_NUM_WORKERS=1" `
  --project=$PROJECT_ID

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✓ Deployment Successful!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next code change will only rebuild the last 2 layers (~5 seconds)" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "✗ Deployment failed" -ForegroundColor Red
}
