# Deploy GrooveSheet Microservices Architecture to Google Cloud
# This script deploys both API and Worker services with Pub/Sub and GCS

# Configuration
$PROJECT_ID = "groovesheet2025"
$REGION = "asia-southeast1"
$API_SERVICE_NAME = "groovesheet-api"
$WORKER_SERVICE_NAME = "groovesheet-worker"
$BUCKET_NAME = "groovesheet-jobs"
$TOPIC_NAME = "groovesheet-worker-tasks"
$SUBSCRIPTION_NAME = "groovesheet-worker-tasks-sub"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Deploying GrooveSheet Microservices to GCP" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Project ID: $PROJECT_ID" -ForegroundColor Gray
Write-Host "  Region: $REGION" -ForegroundColor Gray
Write-Host "  API Service: $API_SERVICE_NAME" -ForegroundColor Gray
Write-Host "  Worker Service: $WORKER_SERVICE_NAME" -ForegroundColor Gray
Write-Host "  GCS Bucket: gs://$BUCKET_NAME" -ForegroundColor Gray
Write-Host "  Pub/Sub Topic: $TOPIC_NAME" -ForegroundColor Gray
Write-Host ""

# Set GCloud project
Write-Host "[1/8] Setting GCloud project..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Failed to set project" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Project set to $PROJECT_ID" -ForegroundColor Green
Write-Host ""

# Enable required APIs
Write-Host "[2/8] Enabling required Google Cloud APIs..." -ForegroundColor Yellow
Write-Host "  Enabling Cloud Run API..." -ForegroundColor Gray
gcloud services enable run.googleapis.com --project=$PROJECT_ID
Write-Host "  Enabling Cloud Build API..." -ForegroundColor Gray
gcloud services enable cloudbuild.googleapis.com --project=$PROJECT_ID
Write-Host "  Enabling Pub/Sub API..." -ForegroundColor Gray
gcloud services enable pubsub.googleapis.com --project=$PROJECT_ID
Write-Host "  Enabling Storage API..." -ForegroundColor Gray
gcloud services enable storage.googleapis.com --project=$PROJECT_ID
Write-Host "  ✓ APIs enabled" -ForegroundColor Green
Write-Host ""

# Create GCS bucket
Write-Host "[3/8] Setting up Cloud Storage bucket..." -ForegroundColor Yellow
$bucketCheck = gcloud storage buckets describe "gs://$BUCKET_NAME" --project=$PROJECT_ID 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Bucket gs://$BUCKET_NAME already exists" -ForegroundColor Green
} else {
    Write-Host "  Creating bucket gs://$BUCKET_NAME..." -ForegroundColor Gray
    gcloud storage buckets create "gs://$BUCKET_NAME" --project=$PROJECT_ID --location=$REGION
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Bucket created successfully" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Failed to create bucket" -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

# Create Pub/Sub topic
Write-Host "[4/8] Setting up Pub/Sub topic..." -ForegroundColor Yellow
$topicExists = gcloud pubsub topics describe $TOPIC_NAME --project=$PROJECT_ID 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Topic $TOPIC_NAME already exists" -ForegroundColor Green
} else {
    Write-Host "  Creating topic $TOPIC_NAME..." -ForegroundColor Gray
    gcloud pubsub topics create $TOPIC_NAME --project=$PROJECT_ID
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Topic created successfully" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Failed to create topic" -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

# Create Pub/Sub subscription
Write-Host "[5/8] Setting up Pub/Sub subscription..." -ForegroundColor Yellow
$subExists = gcloud pubsub subscriptions describe $SUBSCRIPTION_NAME --project=$PROJECT_ID 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Subscription $SUBSCRIPTION_NAME already exists" -ForegroundColor Green
} else {
    Write-Host "  Creating subscription $SUBSCRIPTION_NAME..." -ForegroundColor Gray
    gcloud pubsub subscriptions create $SUBSCRIPTION_NAME --topic=$TOPIC_NAME --project=$PROJECT_ID
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Subscription created successfully" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Failed to create subscription" -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

# Build and deploy API service
Write-Host "[6/8] Building and deploying API service..." -ForegroundColor Yellow
Write-Host "  Building Docker image for API..." -ForegroundColor Gray
Set-Location "d:\Coding Files\GitHub\groovesheet\groovesheet-be"
gcloud builds submit --tag "gcr.io/$PROJECT_ID/$API_SERVICE_NAME" --timeout=15m ./api-service
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Failed to build API image" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ API image built successfully" -ForegroundColor Green

Write-Host "  Deploying API service to Cloud Run..." -ForegroundColor Gray
gcloud run deploy $API_SERVICE_NAME `
  --image "gcr.io/$PROJECT_ID/$API_SERVICE_NAME" `
  --platform managed `
  --region $REGION `
  --memory 1Gi `
  --cpu 1 `
  --timeout 60 `
  --concurrency 80 `
  --min-instances 0 `
  --max-instances 10 `
  --allow-unauthenticated `
  --set-env-vars "USE_CLOUD_STORAGE=true,GCS_BUCKET_NAME=$BUCKET_NAME,WORKER_TOPIC=$TOPIC_NAME,GCP_PROJECT=$PROJECT_ID" `
  --project=$PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Failed to deploy API service" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ API service deployed successfully" -ForegroundColor Green
Write-Host ""

# Build and deploy Worker service
Write-Host "[7/8] Building and deploying Worker service..." -ForegroundColor Yellow
Write-Host "  Building Docker image for Worker (this may take 10-15 minutes)..." -ForegroundColor Gray
Write-Host "  Note: Worker image is large due to ML dependencies" -ForegroundColor Gray
gcloud builds submit --tag "gcr.io/$PROJECT_ID/$WORKER_SERVICE_NAME" --timeout=30m -f worker-service/Dockerfile .
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Failed to build Worker image" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Worker image built successfully" -ForegroundColor Green

Write-Host "  Deploying Worker service to Cloud Run..." -ForegroundColor Gray
gcloud run deploy $WORKER_SERVICE_NAME `
  --image "gcr.io/$PROJECT_ID/$WORKER_SERVICE_NAME" `
  --platform managed `
  --region $REGION `
  --memory 8Gi `
  --cpu 4 `
  --timeout 3600 `
  --concurrency 1 `
  --min-instances 0 `
  --max-instances 3 `
  --no-allow-unauthenticated `
  --set-env-vars "USE_CLOUD_STORAGE=true,GCS_BUCKET_NAME=$BUCKET_NAME,PUBSUB_SUBSCRIPTION=$SUBSCRIPTION_NAME,GCP_PROJECT=$PROJECT_ID,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,LOG_LEVEL=INFO,DEMUCS_DEVICE=cpu,TF_CPP_MIN_LOG_LEVEL=3" `
  --project=$PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Failed to deploy Worker service" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Worker service deployed successfully" -ForegroundColor Green
Write-Host ""

# Get service URLs
Write-Host "[8/8] Getting service information..." -ForegroundColor Yellow
$API_URL = gcloud run services describe $API_SERVICE_NAME --region $REGION --format='value(status.url)' --project=$PROJECT_ID
$WORKER_URL = gcloud run services describe $WORKER_SERVICE_NAME --region $REGION --format='value(status.url)' --project=$PROJECT_ID

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Deployment Complete! 🎉" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API Service:" -ForegroundColor Yellow
Write-Host "  URL: $API_URL" -ForegroundColor White
Write-Host "  Health: $API_URL/health" -ForegroundColor Gray
Write-Host "  Transcribe: $API_URL/api/v1/transcribe" -ForegroundColor Gray
Write-Host ""
Write-Host "Worker Service:" -ForegroundColor Yellow
Write-Host "  URL: $WORKER_URL" -ForegroundColor White
Write-Host "  Status: Private (no public access)" -ForegroundColor Gray
Write-Host ""
Write-Host "Infrastructure:" -ForegroundColor Yellow
Write-Host "  GCS Bucket: gs://$BUCKET_NAME" -ForegroundColor White
Write-Host "  Pub/Sub Topic: $TOPIC_NAME" -ForegroundColor White
Write-Host "  Pub/Sub Subscription: $SUBSCRIPTION_NAME" -ForegroundColor White
Write-Host ""
Write-Host "Test your deployment:" -ForegroundColor Green
Write-Host "  curl `"$API_URL/health`"" -ForegroundColor Yellow
Write-Host ""
Write-Host "Note: Worker processes jobs from Pub/Sub automatically" -ForegroundColor Gray
Write-Host "It will scale to 0 when idle and scale up when jobs arrive" -ForegroundColor Gray
Write-Host ""
