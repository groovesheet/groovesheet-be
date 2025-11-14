# GCP Migration: groovesheet-worker → annoteator-worker

This document outlines the steps needed to rename the Cloud Run service from `groovesheet-worker` to `annoteator-worker` in Google Cloud Platform.

## Files Changed in Codebase

The following files have been updated to reference `annoteator-worker` instead of `groovesheet-worker`:

### Configuration Files
- ✅ `annoteator-worker/cloudbuild.yaml` - Updated image name
- ✅ All `deploy-scripts/*.ps1` - Updated service name and image references
- ✅ `MICROSERVICES_README.md` - Updated documentation
- ✅ `README.md` - Updated references

### What Changed
- **Container Image Name**: `gcr.io/groovesheet2025/groovesheet-worker` → `gcr.io/groovesheet2025/annoteator-worker`
- **Cloud Run Service Name**: `groovesheet-worker` → `annoteator-worker`
- **Log Queries**: Updated to use `resource.labels.service_name=annoteator-worker`

### What Stayed the Same
- **Pub/Sub Topic**: `groovesheet-worker-tasks` (no change needed)
- **Pub/Sub Subscription**: `groovesheet-worker-tasks-sub` (no change needed)
- **GCS Bucket**: `groovesheet-jobs` (no change needed)

## GCP Migration Steps

### Option 1: Clean Migration (Recommended)

This creates a new service alongside the old one, allowing you to test before deleting the old service.

#### Step 1: Build and Push New Image
```bash
# Build the new image with the new name
gcloud builds submit --config=annoteator-worker/cloudbuild.yaml --project=groovesheet2025

# OR build locally and push
docker build --platform=linux/amd64 -t gcr.io/groovesheet2025/annoteator-worker:latest -f annoteator-worker/Dockerfile .
docker push gcr.io/groovesheet2025/annoteator-worker:latest
```

#### Step 2: Deploy New Service
```bash
gcloud run deploy annoteator-worker \
  --image gcr.io/groovesheet2025/annoteator-worker:latest \
  --platform managed \
  --region asia-southeast1 \
  --memory 32Gi \
  --cpu 8 \
  --no-cpu-throttling \
  --timeout 3600 \
  --concurrency 1 \
  --min-instances 1 \
  --max-instances 3 \
  --no-allow-unauthenticated \
  --set-env-vars "USE_CLOUD_STORAGE=true,GCS_BUCKET_NAME=groovesheet-jobs,WORKER_SUBSCRIPTION=groovesheet-worker-tasks-sub,GCP_PROJECT=groovesheet2025,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,LOG_LEVEL=INFO,DEMUCS_DEVICE=cpu,TF_CPP_MIN_LOG_LEVEL=3,OMP_NUM_THREADS=4,DEMUCS_NUM_WORKERS=1" \
  --project=groovesheet2025
```

#### Step 3: Verify New Service Works
```bash
# Check service status
gcloud run services describe annoteator-worker --region=asia-southeast1 --project=groovesheet2025

# Monitor logs
gcloud logging read "resource.labels.service_name=annoteator-worker" --limit=20 --project=groovesheet2025

# Test with a job submission (via API)
```

#### Step 4: Delete Old Service (After Verification)
```bash
# Delete the old service
gcloud run services delete groovesheet-worker \
  --region asia-southeast1 \
  --project=groovesheet2025

# Optional: Delete old container images to save storage costs
gcloud container images delete gcr.io/groovesheet2025/groovesheet-worker:latest --force-delete-tags --project=groovesheet2025
```

### Option 2: Direct Rename (Faster, but less safe)

If you're confident and want to rename directly:

#### Step 1: Build New Image
```bash
gcloud builds submit --config=annoteator-worker/cloudbuild.yaml --project=groovesheet2025
```

#### Step 2: Update Existing Service
```bash
# Update the service name (this will create a new revision)
gcloud run services update groovesheet-worker \
  --image gcr.io/groovesheet2025/annoteator-worker:latest \
  --region asia-southeast1 \
  --project=groovesheet2025

# Note: Cloud Run doesn't support renaming services directly.
# You'll need to create a new service and delete the old one.
```

Actually, Cloud Run doesn't support renaming services. You must use Option 1.

## Important Notes

### IAM Permissions
The new service will need the same IAM permissions as the old one:
- **Cloud Run Invoker** (if needed for API calls)
- **Pub/Sub Subscriber** (for `groovesheet-worker-tasks-sub`)
- **Storage Object Admin** (for GCS bucket `groovesheet-jobs`)

Check current permissions:
```bash
# Check old service permissions
gcloud run services get-iam-policy groovesheet-worker --region=asia-southeast1 --project=groovesheet2025

# Apply same permissions to new service
gcloud run services set-iam-policy annoteator-worker policy.yaml --region=asia-southeast1 --project=groovesheet2025
```

### Pub/Sub Subscription
The Pub/Sub subscription `groovesheet-worker-tasks-sub` will continue to work with the new service since:
- The subscription name hasn't changed
- The subscription is configured via environment variable `WORKER_SUBSCRIPTION=groovesheet-worker-tasks-sub`
- Both services can subscribe to the same subscription (but only one should be active)

**Important**: Make sure to delete the old service before the new one starts processing, or you'll have duplicate message processing.

### Monitoring & Logging
Update any monitoring dashboards or alerts that reference:
- `resource.labels.service_name=groovesheet-worker` → `resource.labels.service_name=annoteator-worker`

### Cost Considerations
- Both services will consume resources while both exist
- Old service should be deleted promptly after verification
- Old container images can be deleted to save storage costs

## Verification Checklist

After migration, verify:

- [ ] New service `annoteator-worker` is running
- [ ] Service has `min-instances=1` set
- [ ] Service can pull messages from `groovesheet-worker-tasks-sub`
- [ ] Service can read/write to GCS bucket `groovesheet-jobs`
- [ ] Test job completes successfully
- [ ] Logs are accessible with new service name
- [ ] Old service `groovesheet-worker` is deleted
- [ ] Old container images are cleaned up (optional)

## Rollback Plan

If something goes wrong:

1. **Revert code changes** (git revert or checkout previous commit)
2. **Redeploy old service**:
   ```bash
   gcloud run deploy groovesheet-worker \
     --image gcr.io/groovesheet2025/groovesheet-worker:latest \
     --region asia-southeast1 \
     --project=groovesheet2025
   ```
3. **Delete new service**:
   ```bash
   gcloud run services delete annoteator-worker \
     --region asia-southeast1 \
     --project=groovesheet2025
   ```

## Quick Migration Script

You can also use the updated deploy scripts which now reference `annoteator-worker`:

```bash
# Fast deployment (recommended)
./deploy-scripts/deploy-fast.ps1

# Or full deployment
./deploy-scripts/cloud-build-deploy.ps1
```

These scripts will automatically use the new service name and image.

