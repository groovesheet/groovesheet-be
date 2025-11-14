# Test Full Microservices System with Real MP3
# Tests the cleaned system end-to-end: API + Worker + Pub/Sub
# Usage: .\test-full-system.ps1 [path\to\audio.mp3]

param(
    [string]$TestMp3 = "D:\Coding Files\GitHub\groovesheet\groovesheet-be\testmusic.mp3"
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Configuration
$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot
$API_URL = "http://localhost:8080"

Set-Location $PROJECT_ROOT

Write-ColorOutput "`n========================================" -Color Cyan
Write-ColorOutput "  Testing Full Microservices System" -Color Cyan
Write-ColorOutput "========================================`n" -Color Cyan

# Check if test MP3 exists
if (-not (Test-Path $TestMp3)) {
    Write-ColorOutput "❌ Test MP3 not found: $TestMp3" -Color Red
    Write-ColorOutput "Please ensure the test file exists" -Color Yellow
    exit 1
}

# Get file info
$fileInfo = Get-Item $TestMp3
$FILE_NAME = $fileInfo.Name
$FILE_SIZE = "{0:N2} MB" -f ($fileInfo.Length / 1MB)

Write-ColorOutput "🎵 Test file: $FILE_NAME" -Color Green
Write-ColorOutput "📁 Size: $FILE_SIZE" -Color Gray
Write-Host ""

# Step 1: Start the microservices system
Write-ColorOutput "Step 1: Starting microservices system (LOCAL MODE)..." -Color Yellow
Write-ColorOutput "Stopping any existing containers..." -Color Gray
$prevErrorAction = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
docker-compose -f docker-compose.local.yml down *>&1 | Out-Null
$ErrorActionPreference = $prevErrorAction

# Clean old jobs (keep uploads folder if present)
Write-ColorOutput "Cleaning previous local jobs..." -Color Gray
$localJobsPath = Join-Path $PROJECT_ROOT "testing\local-jobs"
if (Test-Path $localJobsPath) {
    Get-ChildItem $localJobsPath -Directory | Where-Object { $_.Name -ne 'uploads' } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem $localJobsPath -File | Remove-Item -Force -ErrorAction SilentlyContinue
}

Write-ColorOutput "Building and starting services..." -Color Gray
$buildResult = docker-compose -f docker-compose.local.yml up --build -d 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput "❌ Failed to start microservices" -Color Red
    Write-Host ($buildResult | Out-String)
    exit 1
}

Write-ColorOutput "✅ Services started`n" -Color Green

# Step 2: Wait for services to be ready
Write-ColorOutput "Step 2: Waiting for services to be ready..." -Color Yellow
Write-ColorOutput "Checking API health..." -Color Gray

$maxRetries = 10
$retryCount = 0
$apiReady = $false

while ($retryCount -lt $maxRetries -and -not $apiReady) {
    try {
        $response = Invoke-RestMethod -Uri "$API_URL/health" -Method Get -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response -match "healthy|OK" -or $response -eq "OK") {
            $apiReady = $true
            Write-ColorOutput "✅ API service is ready" -Color Green
        }
    }
    catch {
        # API not ready yet
    }
    
    if (-not $apiReady) {
        $retryCount++
        Write-ColorOutput "  Attempt $retryCount/$maxRetries - waiting..." -Color Gray
        Start-Sleep -Seconds 3
    }
}

if (-not $apiReady) {
    Write-ColorOutput "❌ API service failed to become ready" -Color Red
    Write-ColorOutput "Checking logs..." -Color Yellow
    docker-compose -f docker-compose.local.yml logs api
    exit 1
}

# Check worker container status
Write-ColorOutput "Checking worker status..." -Color Gray
$workerStatus = docker-compose -f docker-compose.local.yml ps worker --format "{{.Status}}" 2>$null
if (-not $workerStatus) { $workerStatus = "unknown" }
Write-ColorOutput "  Worker status: $workerStatus`n" -Color Gray

# Step 3: Submit job to API
Write-ColorOutput "Step 3: Submitting transcription job..." -Color Yellow

# Create multipart form data
$boundary = [System.Guid]::NewGuid().ToString()
$fileBin = [System.IO.File]::ReadAllBytes($TestMp3)
$encoding = [System.Text.Encoding]::GetEncoding("iso-8859-1")

$bodyLines = @(
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"$FILE_NAME`"",
    "Content-Type: audio/mpeg",
    "",
    $encoding.GetString($fileBin),
    "--$boundary--"
)

$body = $bodyLines -join "`r`n"

try {
    $response = Invoke-WebRequest -Uri "$API_URL/api/v1/transcribe" -Method Post `
        -Headers @{
            "Authorization" = "Bearer test-token-for-local-testing"
            "Content-Type" = "multipart/form-data; boundary=$boundary"
        } `
        -Body $encoding.GetBytes($body) `
        -TimeoutSec 30
    
    $jobResponse = $response.Content | ConvertFrom-Json
    $jobId = $jobResponse.job_id
    
    if (-not $jobId) {
        throw "Failed to extract job_id from response"
    }
    
    Write-ColorOutput "✅ Job submitted successfully" -Color Green
    Write-ColorOutput "  Job ID: $jobId`n" -Color Cyan
}
catch {
    Write-ColorOutput "❌ Failed to submit job" -Color Red
    Write-ColorOutput "Error: $_" -Color Yellow
    Write-ColorOutput "Checking API logs..." -Color Yellow
    docker-compose -f docker-compose.local.yml logs api
    exit 1
}

# Step 4: Monitor job progress
Write-ColorOutput "Step 4: Monitoring job progress..." -Color Yellow
Write-ColorOutput "This may take 2-3 minutes for the full transcription`n" -Color Gray

$maxWaitMinutes = 10
$startTime = Get-Date
$lastProgress = -1
$status = ""
$downloadUrl = ""

while ($true) {
    try {
        $statusResponse = Invoke-RestMethod -Uri "$API_URL/api/v1/status/$jobId" -Method Get -TimeoutSec 10
        $elapsed = ((Get-Date) - $startTime).TotalMinutes
        $progress = if ($statusResponse.progress) { $statusResponse.progress } else { 0 }
        $status = if ($statusResponse.status) { $statusResponse.status } else { "unknown" }
        
        # Only show progress updates when they change
        if ($progress -ne $lastProgress) {
            Write-Host ("  [{0:N1} min] Status: {1} | Progress: {2}%" -f $elapsed, $status, $progress)
            $lastProgress = $progress
        }
        
        # Check if completed
        if ($status -eq "completed") {
            Write-Host ""
            Write-ColorOutput "✅ Transcription completed successfully!" -Color Green
            Write-ColorOutput ("  Total time: {0:N1} minutes" -f $elapsed) -Color Cyan
            Write-ColorOutput "  Final progress: $progress%" -Color Cyan
            
            # Show download URL if available
            $downloadUrl = $statusResponse.download_url
            if ($downloadUrl) {
                Write-ColorOutput "  Download URL: $downloadUrl" -Color Gray
            }
            
            break
        }
        
        # Check if failed
        if ($status -eq "failed") {
            Write-Host ""
            Write-ColorOutput "❌ Job failed" -Color Red
            Write-ColorOutput ("Response: " + ($statusResponse | ConvertTo-Json)) -Color Yellow
            break
        }
        
        # Check timeout
        if ($elapsed -gt $maxWaitMinutes) {
            Write-Host ""
            Write-ColorOutput "❌ Job timed out after $maxWaitMinutes minutes" -Color Red
            Write-ColorOutput "Last status: $status ($progress%)" -Color Yellow
            break
        }
        
        Start-Sleep -Seconds 5
    }
    catch {
        Write-Host "  Error checking status" -ForegroundColor Red
        Start-Sleep -Seconds 10
    }
}

Write-Host ""

# Step 5: Show logs for debugging
Write-ColorOutput "Step 5: System logs (last 20 lines each)...`n" -Color Yellow

Write-ColorOutput "API Logs:" -Color Cyan
Write-ColorOutput "----------------------------------------" -Color Gray
docker-compose -f docker-compose.local.yml logs --tail=20 api

Write-Host ""
Write-ColorOutput "Worker Logs:" -Color Cyan
Write-ColorOutput "----------------------------------------" -Color Gray
docker-compose -f docker-compose.local.yml logs --tail=20 worker

Write-Host ""

# Step 6: Test download if job completed successfully
if ($status -eq "completed" -and $downloadUrl) {
    Write-ColorOutput "Step 6: Testing download..." -Color Yellow
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $downloadPath = Join-Path $PROJECT_ROOT "test_output_${timestamp}.musicxml"
    
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $downloadPath -TimeoutSec 30
        if (Test-Path $downloadPath) {
            $dlFileInfo = Get-Item $downloadPath
            $dlFileSize = "{0:N2} KB" -f ($dlFileInfo.Length / 1KB)
            Write-ColorOutput "✅ Download successful" -Color Green
            Write-ColorOutput "  File: $downloadPath" -Color Cyan
            Write-ColorOutput "  Size: $dlFileSize" -Color Gray
        }
    }
    catch {
        Write-ColorOutput "❌ Download failed" -Color Red
    }
}

Write-Host ""
Write-ColorOutput "========================================" -Color Cyan

if ($status -eq "completed") {
    Write-ColorOutput "  ✅ FULL SYSTEM TEST PASSED" -Color Green
    Write-ColorOutput "  All microservices working correctly!" -Color Green
}
else {
    Write-ColorOutput "  ❌ FULL SYSTEM TEST FAILED" -Color Red
    Write-ColorOutput "  Check logs above for details" -Color Yellow
}

Write-ColorOutput "========================================`n" -Color Cyan

# Cleanup option
$cleanup = Read-Host "Stop containers? (y/n)"
if ($cleanup -eq "y" -or $cleanup -eq "Y") {
    Write-ColorOutput "Stopping containers..." -Color Gray
    docker-compose -f docker-compose.local.yml down
    Write-ColorOutput "✅ Containers stopped" -Color Green
}
