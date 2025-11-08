# Deploy Worker Service to Cloud Run
# Run this after the worker image build completes

Write-Host "Deploying Worker Service to Cloud Run..." -ForegroundColor Cyan
Write-Host ""

gcloud run deploy groovesheet-worker `
  --image gcr.io/groovesheet2025/groovesheet-worker `
  --platform managed `
  --region asia-southeast1 `
  --memory 8Gi `
  --cpu 4 `
  --timeout 3600 `
  --concurrency 1 `
  --min-instances 0 `
  --max-instances 3 `
  --no-allow-unauthenticated `
  --set-env-vars "USE_CLOUD_STORAGE=true,GCS_BUCKET_NAME=groovesheet-jobs,PUBSUB_SUBSCRIPTION=groovesheet-worker-tasks-sub,GCP_PROJECT=groovesheet2025,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,LOG_LEVEL=INFO,DEMUCS_DEVICE=cpu,TF_CPP_MIN_LOG_LEVEL=3" `
  --project=groovesheet2025

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Worker Deployed Successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "The worker is now listening to Pub/Sub and will process jobs automatically." -ForegroundColor White
    Write-Host ""
    Write-Host "Test your deployment:" -ForegroundColor Yellow
    Write-Host "1. Open http://localhost:3000 in your browser" -ForegroundColor Gray
    Write-Host "2. Upload an MP3 file" -ForegroundColor Gray
    Write-Host "3. Watch it process in real-time!" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "Deployment failed. Check the error above." -ForegroundColor Red
    Write-Host ""
}
