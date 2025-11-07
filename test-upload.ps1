# Test Cloud Run deployment by uploading audio file
$API_URL = "https://groovesheet-be-khr42kbwwa-as.a.run.app"
$AudioFile = "d:\Coding Files\GitHub\groovesheet\groovesheet-be\AnNOTEator\sound_sample\drum.wav"

Write-Host "Testing Cloud Run deployment..." -ForegroundColor Cyan
Write-Host "Service URL: $API_URL" -ForegroundColor Gray
Write-Host "Audio file: $AudioFile" -ForegroundColor Gray
Write-Host ""

# Upload file
Write-Host "Uploading audio file..." -ForegroundColor Yellow
$boundary = [System.Guid]::NewGuid().ToString()
$fileContent = [System.IO.File]::ReadAllBytes($AudioFile)
$fileName = [System.IO.Path]::GetFileName($AudioFile)

$bodyLines = @(
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
    "Content-Type: audio/wav",
    "",
    [System.Text.Encoding]::UTF8.GetString($fileContent),
    "--$boundary--"
)
$body = $bodyLines -join "`r`n"

try {
    $response = Invoke-RestMethod -Uri "$API_URL/api/v1/transcription/upload" `
        -Method Post `
        -ContentType "multipart/form-data; boundary=$boundary" `
        -Body $body
    
    Write-Host "✓ Upload successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Job ID: $($response.job_id)" -ForegroundColor Cyan
    Write-Host "Status: $($response.status)" -ForegroundColor Yellow
    Write-Host ""
    
    # Poll for status
    $jobId = $response.job_id
    Write-Host "Checking job status..." -ForegroundColor Yellow
    
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 5
        $statusResponse = Invoke-RestMethod -Uri "$API_URL/api/v1/transcription/status/$jobId"
        
        Write-Host "[$i] Status: $($statusResponse.status) | Progress: $($statusResponse.progress)% | $($statusResponse.message)" -ForegroundColor Gray
        
        if ($statusResponse.status -eq "completed") {
            Write-Host ""
            Write-Host "✓ Job completed successfully!" -ForegroundColor Green
            Write-Host "Result: $($statusResponse.result | ConvertTo-Json -Depth 3)" -ForegroundColor Cyan
            break
        }
        
        if ($statusResponse.status -eq "failed") {
            Write-Host ""
            Write-Host "✗ Job failed!" -ForegroundColor Red
            Write-Host "Error: $($statusResponse.error)" -ForegroundColor Red
            break
        }
    }
} catch {
    Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
}
