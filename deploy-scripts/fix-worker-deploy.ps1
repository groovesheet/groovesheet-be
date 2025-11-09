# Fix Worker Service - Build and Deploy Updated Worker
# This script fixes the stuck job issue by deploying the updated worker code

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fixing Worker Service" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$PROJECT_ID = "groovesheet2025"
$REGION = "asia-southeast1"
$WORKER_IMAGE = "gcr.io/$PROJECT_ID/groovesheet-worker"

Write-Host "Step 1: Verify Pub/Sub configuration..." -ForegroundColor Yellow
Write-Host ""

# Check subscription ack deadline
$subInfo = gcloud pubsub subscriptions describe groovesheet-worker-tasks-sub --project=$PROJECT_ID --format=json | ConvertFrom-Json
$ackDeadline = $subInfo.ackDeadlineSeconds

Write-Host "Current ack deadline: $ackDeadline seconds" -ForegroundColor White

if ($ackDeadline -lt 600) {
    Write-Host "⚠️  Ack deadline is too short ($ackDeadline seconds)" -ForegroundColor Red
    Write-Host "Updating to 600 seconds (10 minutes)..." -ForegroundColor Yellow
    gcloud pubsub subscriptions update groovesheet-worker-tasks-sub --ack-deadline=600 --project=$PROJECT_ID
    Write-Host "✓ Ack deadline updated" -ForegroundColor Green
} else {
    Write-Host "✓ Ack deadline is sufficient ($ackDeadline seconds)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 2: Building worker image with Cloud Build..." -ForegroundColor Yellow
Write-Host ""

# Navigate to backend root
Set-Location "D:\Coding Files\GitHub\groovesheet\groovesheet-be"

# Submit build using cloudbuild.yaml
gcloud builds submit --config=worker-service/cloudbuild.yaml --project=$PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Build failed. Check the error above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ Build completed successfully" -ForegroundColor Green
Write-Host ""

Write-Host "Step 3: Deploying worker to Cloud Run..." -ForegroundColor Yellow
Write-Host ""
Write-Host "⚙️  Configuration (STABLE v1.0 - tested locally):" -ForegroundColor Cyan
Write-Host "   Memory: 32GB" -ForegroundColor White
Write-Host "   CPU: 8 cores" -ForegroundColor White
Write-Host "   Timeout: 3600s (1 hour)" -ForegroundColor White
Write-Host "   Concurrency: 1 (one job at a time)" -ForegroundColor White
Write-Host "   Git Tag: worker-v1.0-stable" -ForegroundColor White
Write-Host ""

gcloud run deploy groovesheet-worker `
  --image $WORKER_IMAGE `
  --platform managed `
  --region $REGION `
  --memory 32Gi `
  --cpu 8 `
  --timeout 3600 `
  --concurrency 1 `
  --min-instances 0 `
  --max-instances 3 `
  --no-allow-unauthenticated `
  --set-env-vars "USE_CLOUD_STORAGE=true,GCS_BUCKET_NAME=groovesheet-jobs,WORKER_SUBSCRIPTION=groovesheet-worker-tasks-sub,GCP_PROJECT=$PROJECT_ID,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,LOG_LEVEL=INFO,DEMUCS_DEVICE=cpu,TF_CPP_MIN_LOG_LEVEL=3,OMP_NUM_THREADS=8" `
  --project=$PROJECT_ID

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✓ Worker Fixed & Deployed!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Changes applied:" -ForegroundColor Cyan
    Write-Host "  • Fixed Pub/Sub ack deadline handling" -ForegroundColor White
    Write-Host "  • Auto-extends ack deadline during long processing" -ForegroundColor White
    Write-Host "  • Prevents duplicate message delivery" -ForegroundColor White
    Write-Host "  • Increased resources: 32GB RAM, 4 CPU cores (tested locally)" -ForegroundColor White
    Write-Host "  • Fixed metadata.json error handling" -ForegroundColor White
    Write-Host "  • Added aggressive stdout/stderr flushing for real-time logs" -ForegroundColor White
    Write-Host ""
    Write-Host "The worker now handles long transcription jobs properly." -ForegroundColor White
    Write-Host ""
    Write-Host "Test your deployment:" -ForegroundColor Yellow
    Write-Host "  1. Upload a file via the frontend" -ForegroundColor Gray
    Write-Host "  2. Monitor logs: gcloud logging read 'resource.labels.service_name=groovesheet-worker' --limit 50 --project=$PROJECT_ID" -ForegroundColor Gray
    Write-Host "  3. Check job status via API" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Deployment failed. Check the error above." -ForegroundColor Red
    exit 1
}
