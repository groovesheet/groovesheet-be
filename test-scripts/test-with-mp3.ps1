# Manual test script for Nirvana MP3
param(
    [Parameter(Mandatory=$true)]
    [string]$Mp3File
)

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "GROOVESHEET - Drum Transcription Test" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Validate file exists
if (-not (Test-Path $Mp3File)) {
    Write-Host "[ERROR] File not found: $Mp3File" -ForegroundColor Red
    exit 1
}

$fileInfo = Get-Item $Mp3File
Write-Host "Input file: $($fileInfo.FullName)" -ForegroundColor Green
Write-Host "File size: $([math]::Round($fileInfo.Length / 1MB, 2)) MB" -ForegroundColor Green
Write-Host ""

# Create shared directory
Write-Host "Setting up shared storage..." -ForegroundColor Yellow
$sharedDir = ".\shared-jobs"
if (Test-Path $sharedDir) {
    Remove-Item $sharedDir -Recurse -Force
}
New-Item -ItemType Directory -Path $sharedDir -Force | Out-Null
Write-Host "Created: $sharedDir" -ForegroundColor Green
Write-Host ""

# Start API service
Write-Host "Starting API service..." -ForegroundColor Yellow
docker run -d --rm `
    -p 8080:8080 `
    -e USE_CLOUD_STORAGE=false `
    -v "${PWD}\shared-jobs:/app/jobs" `
    --name groovesheet-api `
    groovesheet-api:local | Out-Null

Start-Sleep -Seconds 2
Write-Host "API service started on http://localhost:8080" -ForegroundColor Green
Write-Host ""

# Start Worker service  
Write-Host "Starting Worker service..." -ForegroundColor Yellow
docker run -d --rm `
    -e USE_CLOUD_STORAGE=false `
    -e LOCAL_JOBS_DIR=/app/jobs `
    -v "${PWD}\shared-jobs:/app/jobs" `
    --name groovesheet-worker `
    groovesheet-worker:local `
    python worker_local.py | Out-Null

Start-Sleep -Seconds 3
Write-Host "Worker service started" -ForegroundColor Green
Write-Host ""

# Check worker logs
Write-Host "Worker initialization:" -ForegroundColor Yellow
docker logs groovesheet-worker 2>&1 | Select-Object -First 5
Write-Host ""

# Upload file using curl (simpler than .NET HttpClient)
Write-Host "Uploading audio file..." -ForegroundColor Yellow
$uploadUrl = "http://localhost:8080/api/v1/transcribe"

# Create a temporary script to use curl.exe
$curlScript = @"
`$wc = New-Object System.Net.WebClient
`$wc.Headers.Add("Authorization", "Bearer test-token")
Invoke-RestMethod -Uri "$uploadUrl" -Method Post -InFile "$Mp3File" -ContentType "multipart/form-data" -Headers @{Authorization="Bearer test-token"}
"@

try {
    # Simple upload using Invoke-WebRequest
    $boundary = [System.Guid]::NewGuid().ToString()
    $LF = "`r`n"
    
    $bodyLines = (
        "--$boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"$($fileInfo.Name)`"",
        "Content-Type: audio/mpeg$LF",
        [System.IO.File]::ReadAllText($Mp3File),
        "--$boundary--$LF"
    ) -join $LF
    
    $response = Invoke-RestMethod -Uri $uploadUrl `
        -Method Post `
        -ContentType "multipart/form-data; boundary=$boundary" `
        -Body $bodyLines `
        -Headers @{Authorization="Bearer test-token"}
    
    $jobId = $response.job_id
    Write-Host "Upload successful!" -ForegroundColor Green
    Write-Host "Job ID: $jobId" -ForegroundColor Cyan
    Write-Host ""
    
    # Monitor processing
    Write-Host "Monitoring transcription process..." -ForegroundColor Yellow
    Write-Host "(This will take 2-5 minutes depending on song length)" -ForegroundColor Gray
    Write-Host ""
    
    $maxWait = 600  # 10 minutes
    $elapsed = 0
    $completed = $false
    
    while ($elapsed -lt $maxWait -and -not $completed) {
        Start-Sleep -Seconds 5
        $elapsed += 5
        
        try {
            $status = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/status/$jobId"
            
            $mins = [math]::Floor($elapsed / 60)
            $secs = $elapsed % 60
            Write-Host "  [${mins}m ${secs}s] Status: $($status.status) | Progress: $($status.progress)%" -ForegroundColor Cyan
            
            if ($status.status -eq "completed") {
                $completed = $true
                Write-Host ""
                Write-Host "[SUCCESS] Transcription complete!" -ForegroundColor Green
                Write-Host ""
                
                # Download result
                $outputFile = ".\test_output\$($fileInfo.BaseName)_drums.musicxml"
                New-Item -ItemType Directory -Path ".\test_output" -Force | Out-Null
                
                Invoke-WebRequest -Uri "http://localhost:8080/api/v1/download/$jobId" -OutFile $outputFile
                
                Write-Host "MusicXML saved to: $outputFile" -ForegroundColor Green
                Write-Host "File size: $([math]::Round((Get-Item $outputFile).Length / 1KB, 2)) KB" -ForegroundColor Green
                Write-Host ""
                Write-Host "You can open this file in MuseScore to view the drum notation!" -ForegroundColor Yellow
                
            } elseif ($status.status -eq "failed") {
                Write-Host ""
                Write-Host "[ERROR] Processing failed: $($status.error)" -ForegroundColor Red
                break
            }
            
        } catch {
            Write-Host "  [WARNING] Error checking status: $_" -ForegroundColor Yellow
        }
    }
    
    if (-not $completed) {
        Write-Host ""
        Write-Host "[TIMEOUT] Processing did not complete in 10 minutes" -ForegroundColor Yellow
        Write-Host "Check worker logs: docker logs groovesheet-worker" -ForegroundColor Gray
    }
    
} catch {
    Write-Host "[ERROR] Upload failed: $_" -ForegroundColor Red
    Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "To view logs:" -ForegroundColor Yellow
Write-Host "  docker logs groovesheet-api" -ForegroundColor Gray
Write-Host "  docker logs groovesheet-worker" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop services:" -ForegroundColor Yellow
Write-Host "  docker stop groovesheet-api groovesheet-worker" -ForegroundColor Gray
Write-Host "======================================================================" -ForegroundColor Cyan
