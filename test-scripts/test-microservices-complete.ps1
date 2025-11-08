# Complete local test of microservices architecture
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "GROOVESHEET MICROSERVICES - LOCAL TEST" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# Step 1: Create shared jobs directory
Write-Host "Step 1: Setting up shared storage..." -ForegroundColor Yellow
$sharedDir = ".\shared-jobs"
if (Test-Path $sharedDir) {
    Remove-Item $sharedDir -Recurse -Force
}
New-Item -ItemType Directory -Path $sharedDir -Force | Out-Null
Write-Host "  ✓ Created: $sharedDir" -ForegroundColor Green
Write-Host ""

# Step 2: Start API service
Write-Host "Step 2: Starting API service..." -ForegroundColor Yellow
$apiContainer = docker run -d --rm `
    -p 8080:8080 `
    -e USE_CLOUD_STORAGE=false `
    -v "${PWD}\shared-jobs:/app/jobs" `
    --name groovesheet-api-test `
    groovesheet-api:local

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ API service started: $apiContainer" -ForegroundColor Green
    Start-Sleep -Seconds 2
} else {
    Write-Host "  ✗ Failed to start API service" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 3: Start Worker service
Write-Host "Step 3: Starting Worker service..." -ForegroundColor Yellow
$workerContainer = docker run -d --rm `
    -e USE_CLOUD_STORAGE=false `
    -e LOCAL_JOBS_DIR=/app/jobs `
    -v "${PWD}\shared-jobs:/app/jobs" `
    --name groovesheet-worker-test `
    groovesheet-worker:local `
    python worker_local.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Worker service started: $workerContainer" -ForegroundColor Green
    Start-Sleep -Seconds 3
} else {
    Write-Host "  ✗ Failed to start worker service" -ForegroundColor Red
    docker stop groovesheet-api-test
    exit 1
}
Write-Host ""

# Step 4: Check health
Write-Host "Step 4: Health check..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8080/health" -Method GET
    Write-Host "  ✓ API Status: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Health check failed: $_" -ForegroundColor Red
}
Write-Host ""

# Step 5: Check worker logs
Write-Host "Step 5: Worker logs (first 10 lines)..." -ForegroundColor Yellow
docker logs groovesheet-worker-test 2>&1 | Select-Object -First 10
Write-Host ""

# Step 6: Upload test file
$testFile = ".\crepe\tests\sweep.wav"
if (Test-Path $testFile) {
    Write-Host "Step 6: Uploading test file..." -ForegroundColor Yellow
    Write-Host "  File: $testFile" -ForegroundColor Gray
    
    # Use .NET HttpClient for proper multipart upload
    Add-Type -AssemblyName System.Net.Http
    
    $client = New-Object System.Net.Http.HttpClient
    $content = New-Object System.Net.Http.MultipartFormDataContent
    
    $fileStream = [System.IO.File]::OpenRead($testFile)
    $fileContent = New-Object System.Net.Http.StreamContent($fileStream)
    $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("audio/wav")
    $content.Add($fileContent, "file", "sweep.wav")
    
    $client.DefaultRequestHeaders.Add("Authorization", "Bearer test-token")
    
    try {
        $response = $client.PostAsync("http://localhost:8080/api/v1/transcribe", $content).Result
        $result = $response.Content.ReadAsStringAsync().Result
        $json = $result | ConvertFrom-Json
        $jobId = $json.job_id
        
        Write-Host "  ✓ Upload successful!" -ForegroundColor Green
        Write-Host "  Job ID: $jobId" -ForegroundColor Cyan
        Write-Host ""
        
        # Step 7: Monitor processing
        Write-Host "Step 7: Monitoring job processing..." -ForegroundColor Yellow
        $maxAttempts = 60  # 5 minutes max
        $attempt = 0
        $completed = $false
        
        while ($attempt -lt $maxAttempts -and -not $completed) {
            Start-Sleep -Seconds 5
            $attempt++
            
            try {
                $status = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/status/$jobId" -Method GET
                
                $statusSymbol = switch ($status.status) {
                    "queued" { "[QUEUED]" }
                    "processing" { "[PROCESSING]" }
                    "completed" { "[COMPLETE]" }
                    "failed" { "[FAILED]" }
                    default { "[UNKNOWN]" }
                }
                
                Write-Host "  [$attempt] $statusSymbol Status: $($status.status) | Progress: $($status.progress)%" -ForegroundColor Cyan
                
                if ($status.status -eq "completed") {
                    $completed = $true
                    Write-Host ""
                    Write-Host "  [SUCCESS] Processing complete!" -ForegroundColor Green
                    
                    # Step 8: Download result
                    Write-Host ""
                    Write-Host "Step 8: Downloading MusicXML..." -ForegroundColor Yellow
                    $outputFile = ".\test_output\result_$jobId.musicxml"
                    New-Item -ItemType Directory -Path ".\test_output" -Force | Out-Null
                    
                    Invoke-WebRequest -Uri "http://localhost:8080/api/v1/download/$jobId" -OutFile $outputFile
                    
                    if (Test-Path $outputFile) {
                        $fileSize = (Get-Item $outputFile).Length
                        Write-Host "  ✓ Downloaded: $outputFile ($fileSize bytes)" -ForegroundColor Green
                        
                        # Show first few lines
                        Write-Host ""
                        Write-Host "  Preview (first 15 lines):" -ForegroundColor Gray
                        Get-Content $outputFile -TotalCount 15 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
                    }
                    
                } elseif ($status.status -eq "failed") {
                    Write-Host ""
                    Write-Host "  ✗ Processing failed: $($status.error)" -ForegroundColor Red
                    break
                }
                
            } catch {
                Write-Host "  ⚠ Error checking status: $_" -ForegroundColor Yellow
            }
        }
        
        if (-not $completed -and $attempt -ge $maxAttempts) {
            Write-Host ""
            Write-Host "  ⚠ Timeout: Job did not complete in 5 minutes" -ForegroundColor Yellow
        }
        
    } catch {
        Write-Host "  [ERROR] Upload failed: $_" -ForegroundColor Red
    } finally {
        $fileStream.Close()
        $client.Dispose()
    }
} else {
    Write-Host "Step 6: Test file not found" -ForegroundColor Yellow
    Write-Host "  Expected: $testFile" -ForegroundColor Gray
    Write-Host "  You can test manually with your Nirvana MP3:" -ForegroundColor Gray
    Write-Host "  curl -X POST http://localhost:8080/api/v1/transcribe -F 'file=@path/to/nirvana.mp3' -H 'Authorization: Bearer test'" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Test complete! Services are still running." -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Yellow
Write-Host "  docker logs groovesheet-api-test" -ForegroundColor Gray
Write-Host "  docker logs groovesheet-worker-test" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop services:" -ForegroundColor Yellow
Write-Host "  docker stop groovesheet-api-test groovesheet-worker-test" -ForegroundColor Gray
Write-Host ""
