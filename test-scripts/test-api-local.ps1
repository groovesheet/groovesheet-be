# Test script for local API service
$baseUrl = "http://localhost:8080"

Write-Host "Testing Local API Service" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health check
Write-Host "1. Health Check..." -ForegroundColor Yellow
$health = Invoke-RestMethod -Uri "$baseUrl/health" -Method GET
Write-Host "   Status: $($health.status)" -ForegroundColor Green
Write-Host ""

# Test 2: Upload a file (needs an audio file)
$testFile = "d:\Coding Files\GitHub\groovesheet\groovesheet-be\uploads\test.mp3"
if (Test-Path $testFile) {
    Write-Host "2. Uploading test file..." -ForegroundColor Yellow
    
    # Create multipart form data
    $boundary = [System.Guid]::NewGuid().ToString()
    $headers = @{
        "Authorization" = "Bearer test-token-local-mode"
        "Content-Type" = "multipart/form-data; boundary=$boundary"
    }
    
    # Read file bytes
    $fileBytes = [System.IO.File]::ReadAllBytes($testFile)
    $fileName = [System.IO.Path]::GetFileName($testFile)
    
    # Build multipart body
    $bodyLines = @(
        "--$boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
        "Content-Type: audio/mpeg",
        "",
        [System.Text.Encoding]::GetEncoding("iso-8859-1").GetString($fileBytes),
        "--$boundary--"
    )
    $body = $bodyLines -join "`r`n"
    
    try {
        $upload = Invoke-RestMethod -Uri "$baseUrl/api/v1/transcribe" -Method POST -Headers $headers -Body $body
        $jobId = $upload.job_id
        Write-Host "   Job ID: $jobId" -ForegroundColor Green
        Write-Host "   Status: $($upload.status)" -ForegroundColor Green
        Write-Host ""
        
        # Test 3: Check status
        Write-Host "3. Checking job status..." -ForegroundColor Yellow
        $status = Invoke-RestMethod -Uri "$baseUrl/api/v1/status/$jobId" -Method GET
        Write-Host "   Job: $($status.job_id)" -ForegroundColor Green
        Write-Host "   Status: $($status.status)" -ForegroundColor Green
        Write-Host "   Progress: $($status.progress)%" -ForegroundColor Green
        Write-Host ""
        
        Write-Host "✓ All tests passed!" -ForegroundColor Green
    } catch {
        Write-Host "   Error: $_" -ForegroundColor Red
    }
} else {
    Write-Host "2. Skipping upload test - no test file found at: $testFile" -ForegroundColor Yellow
    Write-Host "   You can manually upload with: curl -F 'file=@path/to/audio.mp3' -H 'Authorization: Bearer test' $baseUrl/api/v1/transcribe" -ForegroundColor Gray
}

Write-Host ""
Write-Host "API Service is running at: $baseUrl" -ForegroundColor Cyan
