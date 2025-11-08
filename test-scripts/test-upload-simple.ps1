# Simple upload test for API service
$apiUrl = "http://localhost:8080/api/v1/transcribe"
$testFile = "d:\Coding Files\GitHub\groovesheet\groovesheet-be\crepe\tests\sweep.wav"

Write-Host "Uploading $testFile..." -ForegroundColor Yellow

# Use webclient for multipart upload
Add-Type -AssemblyName System.Net.Http

$client = New-Object System.Net.Http.HttpClient
$content = New-Object System.Net.Http.MultipartFormDataContent

# Add file
$fileStream = [System.IO.File]::OpenRead($testFile)
$fileContent = New-Object System.Net.Http.StreamContent($fileStream)
$fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("audio/wav")
$content.Add($fileContent, "file", "sweep.wav")

# Add auth header
$client.DefaultRequestHeaders.Add("Authorization", "Bearer test-token")

try {
    $response = $client.PostAsync($apiUrl, $content).Result
    $result = $response.Content.ReadAsStringAsync().Result
    
    Write-Host "Response:" -ForegroundColor Green
    Write-Host $result
    
    # Parse job_id from response
    $json = $result | ConvertFrom-Json
    $jobId = $json.job_id
    
    Write-Host "`nJob ID: $jobId" -ForegroundColor Cyan
    
    # Check status
    Write-Host "`nChecking status..." -ForegroundColor Yellow
    $statusUrl = "http://localhost:8080/api/v1/status/$jobId"
    $status = Invoke-RestMethod -Uri $statusUrl -Method GET
    Write-Host "Status: $($status.status)" -ForegroundColor Green
    Write-Host "Progress: $($status.progress)%" -ForegroundColor Green
    
    # Check if file was saved locally
    $localJobDir = "./jobs/$jobId"
    if (Test-Path $localJobDir) {
        Write-Host "`n✓ Job directory created: $localJobDir" -ForegroundColor Green
        Get-ChildItem $localJobDir | ForEach-Object { Write-Host "  - $_" -ForegroundColor Gray }
    }
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
} finally {
    $fileStream.Close()
    $client.Dispose()
}
