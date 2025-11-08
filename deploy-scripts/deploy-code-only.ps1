# Deploy updated backend code to Cloud Run without rebuilding image
# Uses the existing working image

$PROJECT_ID = "groovesheet2025"
$REGION = "asia-southeast1"
$SERVICE_NAME = "groovesheet-be"
$CHECKPOINT_BUCKET = "groovesheet-omnizart-checkpoints"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Deploying Updated Backend Code" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Set correct GCloud project
Write-Host "Setting GCloud project to $PROJECT_ID..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID
Write-Host ""

# Get the working revision (the one before the failed deploy)
Write-Host "Finding working Cloud Run revision..." -ForegroundColor Yellow
$WORKING_IMAGE = "gcr.io/$PROJECT_ID/${SERVICE_NAME}@sha256:24c8dbbea8fd750df03eeb21433731f95ffa7ca908fc0b25548a19ac79bb4223"
Write-Host "  Using working image: $WORKING_IMAGE" -ForegroundColor Green
Write-Host ""

# Deploy with updated environment variables
Write-Host "Deploying service with checkpoint bucket configuration..." -ForegroundColor Yellow
gcloud run deploy $SERVICE_NAME `
  --image $WORKING_IMAGE `
  --platform managed `
  --region $REGION `
  --memory 8Gi `
  --cpu 2 `
  --timeout 3600 `
  --concurrency 1 `
  --max-instances 3 `
  --allow-unauthenticated `
  --set-env-vars "USE_CLOUD_STORAGE=True,GCS_BUCKET_NAME=groovesheet-jobs,OMNIZART_CHECKPOINT_BUCKET=$CHECKPOINT_BUCKET,DEMUCS_DEVICE=cpu,OMNIZART_DEVICE=cpu,MAX_CONCURRENT_JOBS=1,DEBUG=False,LOG_LEVEL=INFO"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Service URL: https://$SERVICE_NAME-khr42kbwwa-as.a.run.app" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: The backend will now download Omnizart checkpoints from GCS on first startup." -ForegroundColor Yellow
Write-Host "This may take 30-60 seconds on the first request." -ForegroundColor Yellow
