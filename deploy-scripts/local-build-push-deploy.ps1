# Quick Deploy - Deploy code changes without Cloud Build
# Use this when only Python code changed (no dependencies)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Quick Worker Deploy (Code Only)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$PROJECT_ID = "groovesheet2025"
$REGION = "asia-southeast1"
$WORKER_IMAGE = "gcr.io/$PROJECT_ID/annoteator-worker"
$TAG = "latest"

Write-Host "This skips Cloud Build and pushes your local Docker image directly." -ForegroundColor Yellow
Write-Host "Only use this for Python code changes (not dependency changes)." -ForegroundColor Yellow
Write-Host ""

# Navigate to backend root
Set-Location "D:\Coding Files\GitHub\groovesheet\groovesheet-be"

Write-Host "Step 1: Building Docker image locally..." -ForegroundColor Yellow
Write-Host ""

docker build --platform=linux/amd64 -f annoteator-worker/Dockerfile -t "${WORKER_IMAGE}:${TAG}" .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ Local build complete" -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Pushing to Google Container Registry..." -ForegroundColor Yellow
Write-Host ""

# Configure Docker to use gcloud credentials
gcloud auth configure-docker gcr.io --quiet

docker push "${WORKER_IMAGE}:${TAG}"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Push failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ Image pushed to GCR" -ForegroundColor Green
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
    Write-Host "  ✓ Deployment Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Test your deployment:" -ForegroundColor Yellow
    Write-Host "  1. Upload a file via frontend" -ForegroundColor Gray
    Write-Host "  2. Check logs: gcloud logging read 'resource.labels.service_name=annoteator-worker' --limit 50" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Deployment failed" -ForegroundColor Red
    exit 1
}
