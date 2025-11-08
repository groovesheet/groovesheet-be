# Deploy backend to Google Cloud Run with persistent job storage
# PowerShell version for Windows

# Configuration
$PROJECT_ID = "groovesheet2025"
$REGION = "asia-southeast1"
$SERVICE_NAME = "groovesheet-be"
$BUCKET_NAME = "groovesheet-jobs"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Deploying Groovesheet Backend to Cloud Run" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Set correct GCloud project
Write-Host "Setting GCloud project to $PROJECT_ID..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID
Write-Host ""

# Step 1: Create GCS bucket for job storage if it doesn't exist
Write-Host "[1/4] Setting up Cloud Storage bucket for job persistence..." -ForegroundColor Yellow
try {
    gsutil ls -b "gs://$BUCKET_NAME" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Bucket gs://$BUCKET_NAME already exists" -ForegroundColor Green
    }
} catch {
    Write-Host "  Creating bucket gs://$BUCKET_NAME..." -ForegroundColor Gray
    gsutil mb -p $PROJECT_ID -l $REGION "gs://$BUCKET_NAME"
    Write-Host "  ✓ Bucket created successfully" -ForegroundColor Green
}
Write-Host ""

# Step 2: Build Docker image
Write-Host "[2/4] Building Docker image..." -ForegroundColor Yellow
Write-Host "  Building from root directory with backend code..." -ForegroundColor Gray
gcloud builds submit --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" --timeout=30m
Write-Host "  ✓ Docker image built successfully" -ForegroundColor Green
Write-Host ""

# Step 3: Deploy to Cloud Run
Write-Host "[3/4] Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $SERVICE_NAME `
  --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" `
  --platform managed `
  --region $REGION `
  --memory 8Gi `
  --cpu 2 `
  --timeout 3600 `
  --concurrency 1 `
  --min-instances 0 `
  --max-instances 3 `
  --allow-unauthenticated `
  --set-env-vars "USE_CLOUD_STORAGE=True,GCS_BUCKET_NAME=$BUCKET_NAME,DEMUCS_DEVICE=cpu,OMNIZART_DEVICE=cpu,MAX_CONCURRENT_JOBS=1,DEBUG=False,LOG_LEVEL=INFO"

Write-Host "  ✓ Service deployed successfully" -ForegroundColor Green
Write-Host ""

# Step 4: Display service URL
Write-Host "[4/4] Getting service URL..." -ForegroundColor Yellow
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)'
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Deployment Complete! 🎉" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service URL: $SERVICE_URL" -ForegroundColor White
Write-Host "Health check: $SERVICE_URL/api/v1/health" -ForegroundColor White
Write-Host ""
Write-Host "Job storage bucket: gs://$BUCKET_NAME" -ForegroundColor White
Write-Host ""
Write-Host "Test your deployment:" -ForegroundColor Green
Write-Host "  curl `"$SERVICE_URL/api/v1/health`"" -ForegroundColor Yellow
Write-Host ""
