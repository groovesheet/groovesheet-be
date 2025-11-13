# Deploy Only - Just deploy the already-pushed image to Cloud Run
# Use this after the image is already in GCR

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deploy Worker to Cloud Run" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$PROJECT_ID = "groovesheet2025"
$REGION = "asia-southeast1"
$WORKER_IMAGE = "gcr.io/$PROJECT_ID/groovesheet-worker:latest"

Write-Host "⚙️  Configuration:" -ForegroundColor Cyan
Write-Host "   Image: $WORKER_IMAGE" -ForegroundColor White
Write-Host "   Memory: 32GB" -ForegroundColor White
Write-Host "   CPU: 8 cores" -ForegroundColor White
Write-Host "   Timeout: 3600s (1 hour)" -ForegroundColor White
Write-Host ""

gcloud run deploy groovesheet-worker `
  --image $WORKER_IMAGE `
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
  --set-env-vars "USE_CLOUD_STORAGE=true,GCS_BUCKET_NAME=groovesheet-jobs,WORKER_SUBSCRIPTION=groovesheet-worker-tasks-sub,GCP_PROJECT=$PROJECT_ID,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,LOG_LEVEL=INFO,DEMUCS_DEVICE=cpu,TF_CPP_MIN_LOG_LEVEL=3,OMP_NUM_THREADS=8,DEMUCS_NUM_WORKERS=1" `
  --project=$PROJECT_ID

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✓ Deployment Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Monitor logs:" -ForegroundColor Yellow
    Write-Host "  gcloud logging read 'resource.labels.service_name=groovesheet-worker' --limit 50 --project=$PROJECT_ID" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Deployment failed" -ForegroundColor Red
    exit 1
}
