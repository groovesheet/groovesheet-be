# Test Full Microservices System with Real MP3
# Tests the NEW architecture: API + AnNOTEator Worker + Pub/Sub Emulator
# Usage: .\new-system-test.ps1 [path\to\audio.mp3]

param(
    [string]$TEST_MP3 = "D:\Coding Files\GitHub\groovesheet\groovesheet-be\Baseline_Nirvana_Testfile.mp3"
)

# Don't stop on errors - we want to capture and display them
$ErrorActionPreference = "Continue"

# Colors for output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Configuration
$PROJECT_ROOT = "D:\Coding Files\GitHub\groovesheet\groovesheet-be"
$API_URL = "http://localhost:8080"

cd $PROJECT_ROOT

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Testing Full Microservices System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if test MP3 exists
if (!(Test-Path $TEST_MP3)) {
    Write-Host "❌ Test MP3 not found: $TEST_MP3" -ForegroundColor Red
    Write-Host "Please ensure the test file exists" -ForegroundColor Yellow
    exit 1
}

Write-Host "🎵 Test file: $(Split-Path -Leaf $TEST_MP3)" -ForegroundColor Green
Write-Host "📁 Size: $([math]::Round((Get-Item $TEST_MP3).Length / 1MB, 2)) MB" -ForegroundColor Gray
Write-Host ""

# Step 1: Start the microservices system
Write-Host "Step 1: Starting microservices system (LOCAL MODE)..." -ForegroundColor Yellow
Write-Host "Stopping any existing containers..." -ForegroundColor Gray
docker-compose -f docker-compose.local.yml down 2>&1 | Out-Host

# Clean old jobs (keep uploads folder if present)
Write-Host "Cleaning previous local jobs..." -ForegroundColor Gray
if (Test-Path "$PROJECT_ROOT\testing\local-jobs") {
    Get-ChildItem "$PROJECT_ROOT\testing\local-jobs" | Where-Object { $_.Name -ne 'uploads' } | ForEach-Object { Remove-Item $_.FullName -Recurse -Force }
}

Write-Host "Building and starting services..." -ForegroundColor Gray
docker-compose -f docker-compose.local.yml up --build -d 2>&1 | Out-Host

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start microservices" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Services started" -ForegroundColor Green
Write-Host ""

# Step 2: Wait for services to be ready
Write-Host "Step 2: Waiting for services to be ready..." -ForegroundColor Yellow
Write-Host "Checking API health..." -ForegroundColor Gray

$maxRetries = 10
$retryCount = 0
$apiReady = $false

while ($retryCount -lt $maxRetries -and !$apiReady) {
    try {
        $response = Invoke-RestMethod -Uri "$API_URL/health" -Method Get -TimeoutSec 5
        if ($response.status -eq "healthy") {
            $apiReady = $true
            Write-Host "✅ API service is ready" -ForegroundColor Green
        }
    }
    catch {
        $retryCount++
        Write-Host "  Attempt $retryCount/$maxRetries - waiting..." -ForegroundColor Gray
        Start-Sleep 3
    }
}

if (!$apiReady) {
    Write-Host "❌ API service failed to become ready" -ForegroundColor Red
    Write-Host "Checking logs..." -ForegroundColor Yellow
    docker-compose -f docker-compose.local.yml logs api
    exit 1
}

# Check worker container status
Write-Host "Checking worker status..." -ForegroundColor Gray
$workerStatus = docker-compose -f docker-compose.local.yml ps worker --format "table {{.Status}}"
Write-Host "  Worker status: $workerStatus" -ForegroundColor Gray

Write-Host ""

# Step 3: Submit job to API
Write-Host "Step 3: Submitting transcription job..." -ForegroundColor Yellow

try {
    # Reliable multipart upload using HttpClient (works on Windows PowerShell 5.1)
    Add-Type -AssemblyName System.Net.Http
    $fileName = Split-Path -Leaf $TEST_MP3
    $httpClient = New-Object System.Net.Http.HttpClient
    $httpClient.Timeout = [TimeSpan]::FromMinutes(10)
    $httpClient.DefaultRequestHeaders.Authorization = New-Object System.Net.Http.Headers.AuthenticationHeaderValue("Bearer","test-token-for-local-testing")
    $multipart = New-Object System.Net.Http.MultipartFormDataContent
    $fs = [System.IO.File]::OpenRead($TEST_MP3)
    $streamContent = New-Object System.Net.Http.StreamContent($fs)
    $streamContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("audio/mpeg")
    $null = $multipart.Add($streamContent, 'file', $fileName)
    $resp = $httpClient.PostAsync("$API_URL/api/v1/transcribe", $multipart).Result
    if (-not $resp.IsSuccessStatusCode) {
        $body = $resp.Content.ReadAsStringAsync().Result
        throw "Upload failed: $($resp.StatusCode) $body"
    }
    $json = $resp.Content.ReadAsStringAsync().Result | ConvertFrom-Json
    $jobId = $json.job_id
    $fs.Dispose()
    $httpClient.Dispose()
    Write-Host "✅ Job submitted successfully" -ForegroundColor Green
    Write-Host "  Job ID: $jobId" -ForegroundColor Cyan
    Write-Host ""
}
catch {
    Write-Host "❌ Failed to submit job: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Checking API logs..." -ForegroundColor Yellow
    docker-compose -f docker-compose.local.yml logs api
    exit 1
}

# Step 4: Monitor job progress
Write-Host "Step 4: Monitoring job progress..." -ForegroundColor Yellow
Write-Host "This may take 2-3 minutes for the full transcription" -ForegroundColor Gray
Write-Host ""

$maxWaitMinutes = 10
$startTime = Get-Date
$lastProgress = -1

while ($true) {
    try {
        # Correct status endpoint
        $statusResponse = Invoke-RestMethod -Uri "$API_URL/api/v1/status/$jobId" -Method Get -TimeoutSec 10
        
        $elapsed = [math]::Round(((Get-Date) - $startTime).TotalMinutes, 1)
        $progress = if ($statusResponse.progress) { $statusResponse.progress } else { 0 }
        $status = $statusResponse.status
        
        # Only show progress updates when they change
        if ($progress -ne $lastProgress) {
            Write-Host "  [$elapsed min] Status: $status | Progress: $progress%" -ForegroundColor White
            $lastProgress = $progress
        }
        
        # Check if completed
        if ($status -eq "completed") {
            Write-Host ""
            Write-Host "✅ Transcription completed successfully!" -ForegroundColor Green
            Write-Host "  Total time: $elapsed minutes" -ForegroundColor Cyan
            Write-Host "  Final progress: $progress%" -ForegroundColor Cyan
            
            # Show download URL if available
            if ($statusResponse.download_url) {
                Write-Host "  Download URL: $($statusResponse.download_url)" -ForegroundColor Gray
            }
            
            break
        }
        
        # Check if failed
        if ($status -eq "failed") {
            Write-Host ""
            Write-Host "❌ Job failed" -ForegroundColor Red
            Write-Host "Response: $($statusResponse | ConvertTo-Json -Depth 3)" -ForegroundColor Yellow
            break
        }
        
        # Check timeout
        if ($elapsed -gt $maxWaitMinutes) {
            Write-Host ""
            Write-Host "❌ Job timed out after $maxWaitMinutes minutes" -ForegroundColor Red
            Write-Host "Last status: $status ($progress%)" -ForegroundColor Yellow
            break
        }
        
        Start-Sleep 5
    }
    catch {
        Write-Host "  Error checking status: $($_.Exception.Message)" -ForegroundColor Red
        Start-Sleep 10
    }
}

Write-Host ""

# Step 5: Show logs for debugging
Write-Host "Step 5: System logs (last 20 lines each)..." -ForegroundColor Yellow
Write-Host ""

Write-Host "API Logs:" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor DarkGray
docker-compose -f docker-compose.local.yml logs --tail=20 api

Write-Host ""
Write-Host "Worker Logs:" -ForegroundColor Cyan  
Write-Host "----------------------------------------" -ForegroundColor DarkGray
docker-compose -f docker-compose.local.yml logs --tail=20 worker

Write-Host ""

# Step 6: Test download if job completed successfully
if ($statusResponse.status -eq "completed" -and $statusResponse.download_url) {
    Write-Host "Step 6: Testing download..." -ForegroundColor Yellow
    
    try {
        $downloadPath = "$PROJECT_ROOT\test_output_$(Get-Date -Format 'yyyyMMdd_HHmmss').musicxml"
        Invoke-WebRequest -Uri "$API_URL$($statusResponse.download_url)" -OutFile $downloadPath -TimeoutSec 30
        
        if (Test-Path $downloadPath) {
            $fileSize = [math]::Round((Get-Item $downloadPath).Length / 1KB, 1)
            Write-Host "✅ Download successful" -ForegroundColor Green
            Write-Host "  File: $downloadPath" -ForegroundColor Cyan
            Write-Host "  Size: $fileSize KB" -ForegroundColor Gray
        }
    }
    catch {
        Write-Host "❌ Download failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($statusResponse.status -eq "completed") {
    Write-Host "  ✅ FULL SYSTEM TEST PASSED" -ForegroundColor Green
    Write-Host "  All microservices working correctly!" -ForegroundColor Green
} else {
    Write-Host "  ❌ FULL SYSTEM TEST FAILED" -ForegroundColor Red
    Write-Host "  Check logs above for details" -ForegroundColor Yellow
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Cleanup option
$cleanup = Read-Host "Stop containers? (y/n)"
if ($cleanup -eq "y" -or $cleanup -eq "Y") {
    Write-Host "Stopping containers..." -ForegroundColor Gray
    docker-compose -f docker-compose.local.yml down
    Write-Host "✅ Containers stopped" -ForegroundColor Green
}
