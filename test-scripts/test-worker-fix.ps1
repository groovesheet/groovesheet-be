# Test Worker Fix
# Quick verification that the worker fix is working correctly

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Testing Worker Fix" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$PROJECT_ID = "groovesheet2025"
$API_URL = "https://groovesheet-api-700212390421.asia-southeast1.run.app"

# Check Pub/Sub subscription configuration
Write-Host "1. Verifying Pub/Sub configuration..." -ForegroundColor Yellow
$subInfo = gcloud pubsub subscriptions describe groovesheet-worker-tasks-sub --project=$PROJECT_ID --format=json | ConvertFrom-Json
$ackDeadline = $subInfo.ackDeadlineSeconds

if ($ackDeadline -ge 600) {
    Write-Host "   ✓ Ack deadline: $ackDeadline seconds (OK)" -ForegroundColor Green
} else {
    Write-Host "   ✗ Ack deadline: $ackDeadline seconds (TOO SHORT)" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Check worker service is running
Write-Host "2. Checking worker service status..." -ForegroundColor Yellow
$workerStatus = gcloud run services describe groovesheet-worker --region=asia-southeast1 --project=$PROJECT_ID --format=json | ConvertFrom-Json
$latestRevision = $workerStatus.status.latestReadyRevisionName

Write-Host "   Latest revision: $latestRevision" -ForegroundColor White
Write-Host "   URL: $($workerStatus.status.url)" -ForegroundColor White

# Check if new revision (with fix)
if ($latestRevision -match "groovesheet-worker-00005") {
    Write-Host "   ✓ Running fixed version" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  May not be running latest version" -ForegroundColor Yellow
}
Write-Host ""

# Check recent logs for any errors
Write-Host "3. Checking recent worker logs..." -ForegroundColor Yellow
$recentErrors = gcloud logging read "resource.labels.service_name=groovesheet-worker AND severity=ERROR" `
    --limit 5 `
    --project=$PROJECT_ID `
    --format="value(timestamp,textPayload)" 2>&1

if ($recentErrors -match "Listed 0 items") {
    Write-Host "   ✓ No recent errors" -ForegroundColor Green
} else {
    Write-Host "   Recent errors found:" -ForegroundColor Yellow
    Write-Host $recentErrors
}
Write-Host ""

# Suggest test steps
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Ready to Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To test the fix:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Upload a file via your frontend" -ForegroundColor White
Write-Host ""
Write-Host "2. Monitor logs in real-time:" -ForegroundColor White
Write-Host "   gcloud logging tail 'resource.labels.service_name=groovesheet-worker' --project=$PROJECT_ID" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Watch for this sequence:" -ForegroundColor White
Write-Host "   - 'Received message for job...' (1 time only!)" -ForegroundColor Gray
Write-Host "   - 'Starting job...' (1 time only!)" -ForegroundColor Gray
Write-Host "   - 'Downloaded input file...'" -ForegroundColor Gray
Write-Host "   - 'Starting transcription...'" -ForegroundColor Gray
Write-Host "   - 'Transcription complete...'" -ForegroundColor Gray
Write-Host "   - 'Job ... completed successfully'" -ForegroundColor Gray
Write-Host "   - 'Acknowledged message for job...'" -ForegroundColor Gray
Write-Host ""
Write-Host "Expected time: 2-4 minutes" -ForegroundColor White
Write-Host ""
Write-Host "❌ Bad sign (old issue): Same job ID appearing multiple times" -ForegroundColor Red
Write-Host "✅ Good sign (fixed): Each job ID appears only once" -ForegroundColor Green
Write-Host ""
