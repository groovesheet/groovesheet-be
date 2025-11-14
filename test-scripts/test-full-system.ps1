# Test Full Microservices System with Real MP3
# Tests the cleaned system end-to-end: API + Worker + Pub/Sub
# Usage: .\test-full-system.ps1 [path/to/audio.mp3]

$ErrorActionPreference = "Stop"

# Configuration
# Default path - update this or pass as first argument
$DEFAULT_TEST_MP3 = "C:\path\to\your\test\file.mp3"
$TEST_MP3 = if ($args.Count -gt 0) { $args[0] } else { $DEFAULT_TEST_MP3 }
$PROJECT_ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$API_URL = "http://localhost:8080"

Set-Location $PROJECT_ROOT

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Testing Full Microservices System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if test MP3 exists
if (-not (Test-Path $TEST_MP3)) {
    Write-Host "❌ Test MP3 not found: $TEST_MP3" -ForegroundColor Red
    Write-Host "Please ensure the test file exists" -ForegroundColor Yellow
    exit 1
}

# Get file info
$FILE_NAME = Split-Path -Leaf $TEST_MP3
$FILE_SIZE = "{0:N2} MB" -f ((Get-Item $TEST_MP3).Length / 1MB)

Write-Host "🎵 Test file: $FILE_NAME" -ForegroundColor Green
Write-Host "📁 Size: $FILE_SIZE" -ForegroundColor Gray
Write-Host ""

# Step 1: Start the microservices system
Write-Host "Step 1: Starting microservices system (LOCAL MODE)..." -ForegroundColor Yellow
Write-Host "Stopping any existing containers..." -ForegroundColor Gray
docker-compose -f docker-compose.local.yml down 2>&1 | Out-Null

# Clean old jobs (keep uploads folder if present)
Write-Host "Cleaning previous local jobs..." -ForegroundColor Gray
$localJobsPath = Join-Path $PROJECT_ROOT "testing\local-jobs"
if (Test-Path $localJobsPath) {
    Get-ChildItem -Path $localJobsPath -Directory | Where-Object { $_.Name -ne "uploads" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Building and starting services..." -ForegroundColor Gray
try {
    docker-compose -f docker-compose.local.yml up --build -d 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker compose failed"
    }
} catch {
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

while ($retryCount -lt $maxRetries -and -not $apiReady) {
    try {
        $response = Invoke-WebRequest -Uri "$API_URL/health" -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        $content = $response.Content
        if ($content -match "healthy|OK" -or $content -eq "OK") {
            $apiReady = $true
            Write-Host "✅ API service is ready" -ForegroundColor Green
        }
    } catch {
        # API not ready yet, continue
    }
    
    if (-not $apiReady) {
        $retryCount++
        Write-Host "  Attempt $retryCount/$maxRetries - waiting..." -ForegroundColor Gray
        Start-Sleep -Seconds 3
    }
}

if (-not $apiReady) {
    Write-Host "❌ API service failed to become ready" -ForegroundColor Red
    Write-Host "Checking logs..." -ForegroundColor Yellow
    docker-compose -f docker-compose.local.yml logs api
    exit 1
}

# Check worker container status
Write-Host "Checking worker status..." -ForegroundColor Gray
try {
    $workerStatus = docker-compose -f docker-compose.local.yml ps worker --format "{{.Status}}" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $workerStatus = "unknown"
    }
} catch {
    $workerStatus = "unknown"
}
Write-Host "  Worker status: $workerStatus" -ForegroundColor Gray
Write-Host ""

# Step 3: Submit job to API
Write-Host "Step 3: Submitting transcription job..." -ForegroundColor Yellow

try {
    # Create multipart form data
    $boundary = [System.Guid]::NewGuid().ToString()
    $fileBytes = [System.IO.File]::ReadAllBytes($TEST_MP3)
    $fileName = Split-Path -Leaf $TEST_MP3
    
    # Build multipart form data manually
    $LF = "`r`n"
    $bodyLines = New-Object System.Collections.ArrayList
    
    # Add file part
    [void]$bodyLines.Add("--$boundary")
    [void]$bodyLines.Add("Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"")
    [void]$bodyLines.Add("Content-Type: audio/mpeg")
    [void]$bodyLines.Add("")
    
    # Combine header and body
    $headerText = $bodyLines -join $LF
    $footer = "$LF--$boundary--$LF"
    
    # Create final body with proper encoding
    $headerBytes = [System.Text.Encoding]::UTF8.GetBytes($headerText + $LF)
    $footerBytes = [System.Text.Encoding]::UTF8.GetBytes($footer)
    
    $bodyBytes = $headerBytes + $fileBytes + $footerBytes
    
    $headers = @{
        "Authorization" = "Bearer test-token-for-local-testing"
        "Content-Type" = "multipart/form-data; boundary=$boundary"
    }
    
    $response = Invoke-WebRequest -Uri "$API_URL/api/v1/transcribe" -Method Post -Headers $headers -Body $bodyBytes -UseBasicParsing -ErrorAction Stop
    
    if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
        Write-Host "❌ Upload failed: HTTP $($response.StatusCode)" -ForegroundColor Red
        Write-Host "Response: $($response.Content)" -ForegroundColor Yellow
        Write-Host "Checking API logs..." -ForegroundColor Yellow
        docker-compose -f docker-compose.local.yml logs api
        exit 1
    }
    
    $responseBody = $response.Content | ConvertFrom-Json
    $jobId = $responseBody.job_id
    
    if ([string]::IsNullOrEmpty($jobId)) {
        Write-Host "❌ Failed to extract job_id from response" -ForegroundColor Red
        Write-Host "Response: $($response.Content)" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ Failed to submit job" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "Checking API logs..." -ForegroundColor Yellow
    docker-compose -f docker-compose.local.yml logs api
    exit 1
}

Write-Host "✅ Job submitted successfully" -ForegroundColor Green
Write-Host "  Job ID: $jobId" -ForegroundColor Cyan
Write-Host ""

# Step 4: Monitor job progress
Write-Host "Step 4: Monitoring job progress..." -ForegroundColor Yellow
Write-Host "This may take 2-3 minutes for the full transcription" -ForegroundColor Gray
Write-Host ""

$maxWaitMinutes = 10
$startTime = Get-Date
$lastProgress = -1
$status = ""

while ($true) {
    try {
        $statusResponse = Invoke-RestMethod -Uri "$API_URL/api/v1/status/$jobId" -Method Get -TimeoutSec 10 -ErrorAction Stop
        
        $elapsed = ((Get-Date) - $startTime).TotalMinutes
        $progress = if ($statusResponse.progress) { $statusResponse.progress } else { 0 }
        $status = if ($statusResponse.status) { $statusResponse.status } else { "unknown" }
        
        # Only show progress updates when they change
        if ($progress -ne $lastProgress) {
            Write-Host "  [$([math]::Round($elapsed, 1)) min] Status: $status | Progress: ${progress}%"
            $lastProgress = $progress
        }
        
        # Check if completed
        if ($status -eq "completed") {
            Write-Host ""
            Write-Host "✅ Transcription completed successfully!" -ForegroundColor Green
            Write-Host "  Total time: $([math]::Round($elapsed, 1)) minutes" -ForegroundColor Cyan
            Write-Host "  Final progress: ${progress}%" -ForegroundColor Cyan
            
            # Show download URL if available
            $downloadUrl = if ($statusResponse.download_url) { $statusResponse.download_url } else { "" }
            if ($downloadUrl) {
                Write-Host "  Download URL: $downloadUrl" -ForegroundColor Gray
            }
            
            break
        }
        
        # Check if failed
        if ($status -eq "failed") {
            Write-Host ""
            Write-Host "❌ Job failed" -ForegroundColor Red
            Write-Host "Response: $($statusResponse | ConvertTo-Json)" -ForegroundColor Yellow
            break
        }
        
        # Check timeout
        if ($elapsed -gt $maxWaitMinutes) {
            Write-Host ""
            Write-Host "❌ Job timed out after $maxWaitMinutes minutes" -ForegroundColor Red
            Write-Host "Last status: $status ($progress%)" -ForegroundColor Yellow
            break
        }
        
        Start-Sleep -Seconds 5
    } catch {
        Write-Host "  Error checking status" -ForegroundColor Red
        Start-Sleep -Seconds 10
    }
}

Write-Host ""

# Step 5: Show logs for debugging
Write-Host "Step 5: System logs (last 20 lines each)..." -ForegroundColor Yellow
Write-Host ""

Write-Host "API Logs:" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Gray
docker-compose -f docker-compose.local.yml logs --tail=20 api

Write-Host ""
Write-Host "Worker Logs:" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Gray
docker-compose -f docker-compose.local.yml logs --tail=20 worker

Write-Host ""

# Step 6: Test download if job completed successfully
if ($status -eq "completed" -and $downloadUrl) {
    Write-Host "Step 6: Testing download..." -ForegroundColor Yellow
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $downloadPath = Join-Path $PROJECT_ROOT "test_output_${timestamp}.musicxml"
    
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $downloadPath -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
        
        if (Test-Path $downloadPath) {
            $fileSize = "{0:N2} MB" -f ((Get-Item $downloadPath).Length / 1MB)
            Write-Host "✅ Download successful" -ForegroundColor Green
            Write-Host "  File: $downloadPath" -ForegroundColor Cyan
            Write-Host "  Size: $fileSize" -ForegroundColor Gray
        }
    } catch {
        Write-Host "❌ Download failed" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($status -eq "completed") {
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

