#!/bin/bash
# Deploy backend to Google Cloud Run with persistent job storage
# This script builds and deploys the backend Docker container with proper environment configuration

# Configuration
PROJECT_ID="groovesheet-438507"
REGION="asia-southeast1"
SERVICE_NAME="groovesheet-be"
BUCKET_NAME="groovesheet-jobs"

echo "======================================"
echo "Deploying Groovesheet Backend to Cloud Run"
echo "======================================"
echo ""

# Step 1: Create GCS bucket for job storage if it doesn't exist
echo "[1/4] Setting up Cloud Storage bucket for job persistence..."
if gsutil ls -b gs://$BUCKET_NAME >/dev/null 2>&1; then
    echo "  ✓ Bucket gs://$BUCKET_NAME already exists"
else
    echo "  Creating bucket gs://$BUCKET_NAME..."
    gsutil mb -p $PROJECT_ID -l $REGION gs://$BUCKET_NAME
    echo "  ✓ Bucket created successfully"
fi
echo ""

# Step 2: Build Docker image
echo "[2/4] Building Docker image..."
cd backend
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME --timeout=30m
echo "  ✓ Docker image built successfully"
echo ""

# Step 3: Deploy to Cloud Run
echo "[3/4] Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --memory 8Gi \
  --cpu 2 \
  --timeout 3600 \
  --concurrency 1 \
  --min-instances 0 \
  --max-instances 3 \
  --allow-unauthenticated \
  --set-env-vars "USE_CLOUD_STORAGE=True,GCS_BUCKET_NAME=$BUCKET_NAME,DEMUCS_DEVICE=cpu,OMNIZART_DEVICE=cpu,MAX_CONCURRENT_JOBS=1,DEBUG=False,LOG_LEVEL=INFO"

echo "  ✓ Service deployed successfully"
echo ""

# Step 4: Display service URL
echo "[4/4] Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')
echo ""
echo "======================================"
echo "Deployment Complete! 🎉"
echo "======================================"
echo ""
echo "Service URL: $SERVICE_URL"
echo "Health check: $SERVICE_URL/api/v1/health"
echo ""
echo "Job storage bucket: gs://$BUCKET_NAME"
echo ""
echo "Test your deployment:"
echo "  curl $SERVICE_URL/api/v1/health"
echo ""
