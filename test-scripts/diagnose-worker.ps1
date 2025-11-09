# Worker Diagnostic Tool
# Check the status of worker service, pub/sub, and recent jobs

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Worker Service Diagnostics" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$PROJECT_ID = "groovesheet2025"
$REGION = "asia-southeast1"

# Check Worker Service Status
Write-Host "1. Worker Service Status:" -ForegroundColor Yellow
Write-Host ""
$workerStatus = gcloud run services describe groovesheet-worker --region=$REGION --project=$PROJECT_ID --format=json | ConvertFrom-Json
Write-Host "  URL: $($workerStatus.status.url)" -ForegroundColor White
Write-Host "  Status: $($workerStatus.status.conditions[0].status)" -ForegroundColor White
Write-Host "  Last Revision: $($workerStatus.status.latestReadyRevisionName)" -ForegroundColor White
Write-Host ""

# Check Pub/Sub Subscription
Write-Host "2. Pub/Sub Subscription:" -ForegroundColor Yellow
Write-Host ""
$subInfo = gcloud pubsub subscriptions describe groovesheet-worker-tasks-sub --project=$PROJECT_ID --format=json | ConvertFrom-Json
Write-Host "  Ack Deadline: $($subInfo.ackDeadlineSeconds) seconds" -ForegroundColor White
Write-Host "  Topic: $($subInfo.topic)" -ForegroundColor White

# Check for undelivered messages
$unacked = gcloud pubsub subscriptions pull groovesheet-worker-tasks-sub --limit=1 --project=$PROJECT_ID 2>&1
if ($unacked -match "Listed 0 items") {
    Write-Host "  Pending Messages: 0" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Pending Messages: Present (see below)" -ForegroundColor Red
    Write-Host $unacked
}
Write-Host ""

# Check Recent Logs
Write-Host "3. Recent Worker Logs (last 10 entries):" -ForegroundColor Yellow
Write-Host ""
gcloud logging read "resource.labels.service_name=groovesheet-worker AND severity>=INFO" `
  --limit 10 `
  --format "table(timestamp,severity,textPayload)" `
  --project=$PROJECT_ID
Write-Host ""

# Check API Service Status
Write-Host "4. API Service Status:" -ForegroundColor Yellow
Write-Host ""
$apiStatus = gcloud run services describe groovesheet-api --region=$REGION --project=$PROJECT_ID --format=json | ConvertFrom-Json
Write-Host "  URL: $($apiStatus.status.url)" -ForegroundColor White
Write-Host "  Status: $($apiStatus.status.conditions[0].status)" -ForegroundColor White
Write-Host ""

# List recent jobs in GCS
Write-Host "5. Recent Jobs in GCS (last 5):" -ForegroundColor Yellow
Write-Host ""
gsutil ls -l gs://groovesheet-jobs/jobs/ | Select-Object -Last 10
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Diagnostic Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Provide recommendations
Write-Host "Recommendations:" -ForegroundColor Yellow
if ($subInfo.ackDeadlineSeconds -lt 600) {
    Write-Host "  ⚠️  Increase ack deadline: gcloud pubsub subscriptions update groovesheet-worker-tasks-sub --ack-deadline=600 --project=$PROJECT_ID" -ForegroundColor Red
}
Write-Host "  • View full logs: gcloud logging read 'resource.labels.service_name=groovesheet-worker' --limit 50 --project=$PROJECT_ID" -ForegroundColor Gray
Write-Host "  • Test health: curl https://groovesheet-worker-700212390421.asia-southeast1.run.app/health" -ForegroundColor Gray
Write-Host "  • Clear stuck messages: gcloud pubsub subscriptions seek groovesheet-worker-tasks-sub --time=$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ') --project=$PROJECT_ID" -ForegroundColor Gray
Write-Host ""
