# Upload Nirvana MP3 to local API
$apiUrl = "http://localhost:8080/api/v1/upload"
$filePath = "D:\Coding Files\GitHub\groovesheet\groovesheet-be\Nirvana - Smells Like Teen Spirit (Official Music Video).mp3"

Write-Host "Uploading file: $filePath" -ForegroundColor Cyan

# Create multipart form data
$boundary = [System.Guid]::NewGuid().ToString()
$LF = "`r`n"

$fileBytes = [System.IO.File]::ReadAllBytes($filePath)
$fileName = [System.IO.Path]::GetFileName($filePath)

$bodyLines = (
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
    "Content-Type: audio/mpeg$LF",
    [System.Text.Encoding]::GetEncoding('iso-8859-1').GetString($fileBytes),
    "--$boundary--$LF"
) -join $LF

$response = Invoke-RestMethod -Uri $apiUrl -Method Post -ContentType "multipart/form-data; boundary=$boundary" -Body $bodyLines -Headers @{
    "Authorization" = "Bearer test-token"
}

Write-Host "`n✓ Upload successful!" -ForegroundColor Green
Write-Host "Job ID: $($response.job_id)" -ForegroundColor Yellow
Write-Host "Status: $($response.status)" -ForegroundColor Cyan

# Save job ID for later use
$response.job_id | Out-File "last-job-id.txt"

return $response
