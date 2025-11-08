# Quick upload for Nirvana MP3
$mp3File = "D:\Coding Files\GitHub\groovesheet\groovesheet-be\Nirvana - Smells Like Teen Spirit (Official Music Video).mp3"

Write-Host "Uploading: $mp3File" -ForegroundColor Cyan
Write-Host ""

# Simple upload
$boundary = [System.Guid]::NewGuid().ToString()
$fileBytes = [System.IO.File]::ReadAllBytes($mp3File)
$fileName = [System.IO.Path]::GetFileName($mp3File)

$LF = "`r`n"
$bodyLines = @(
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
    "Content-Type: audio/mpeg",
    "",
    [System.Text.Encoding]::GetEncoding("iso-8859-1").GetString($fileBytes),
    "--$boundary--"
) -join $LF

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/transcribe" `
        -Method Post `
        -ContentType "multipart/form-data; boundary=$boundary" `
        -Body ([System.Text.Encoding]::GetEncoding("iso-8859-1").GetBytes($bodyLines)) `
        -Headers @{Authorization="Bearer test"}
    
    $jobId = $response.job_id
    Write-Host "Job ID: $jobId" -ForegroundColor Green
    Write-Host ""
    Write-Host "Monitoring progress (this will take 2-5 minutes)..." -ForegroundColor Yellow
    Write-Host ""
    
    # Monitor
    $maxAttempts = 120
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        Start-Sleep -Seconds 5
        $attempt++
        
        $status = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/status/$jobId"
        
        $elapsed = $attempt * 5
        $mins = [math]::Floor($elapsed / 60)
        $secs = $elapsed % 60
        
        Write-Host "  [${mins}m ${secs}s] Status: $($status.status.PadRight(12)) Progress: $($status.progress)%" -ForegroundColor Cyan
        
        if ($status.status -eq "completed") {
            Write-Host ""
            Write-Host "SUCCESS! Downloading MusicXML..." -ForegroundColor Green
            
            $outputFile = ".\test_output\Nirvana_drums.musicxml"
            New-Item -ItemType Directory -Path ".\test_output" -Force | Out-Null
            Invoke-WebRequest -Uri "http://localhost:8080/api/v1/download/$jobId" -OutFile $outputFile
            
            Write-Host "Saved to: $outputFile" -ForegroundColor Green
            Write-Host "Size: $([math]::Round((Get-Item $outputFile).Length / 1KB, 2)) KB" -ForegroundColor Green
            Write-Host ""
            Write-Host "Open this file in MuseScore to view the drum notation!" -ForegroundColor Yellow
            break
            
        } elseif ($status.status -eq "failed") {
            Write-Host ""
            Write-Host "ERROR: $($status.error)" -ForegroundColor Red
            break
        }
    }
    
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}
