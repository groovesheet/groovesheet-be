# Simple test script using Invoke-WebRequest with proper multipart form
$API_URL = "https://groovesheet-be-khr42kbwwa-as.a.run.app"
$AudioFile = "d:\Coding Files\GitHub\groovesheet\groovesheet-be\AnNOTEator\sound_sample\drum.wav"

Write-Host "Testing upload to Cloud Run..." -ForegroundColor Cyan
Write-Host ""

# Create multipart form
$fileBin = [System.IO.File]::ReadAllBytes($AudioFile)
$enc = [System.Text.Encoding]::GetEncoding("iso-8859-1")
$fileEnc = $enc.GetString($fileBin)
$boundary = [System.Guid]::NewGuid().ToString()

$LF = "`r`n"
$bodyLines = ( 
    "--$boundary",
    "Content-Disposition: form-data; name=`"audio_file`"; filename=`"drum.wav`"",
    "Content-Type: audio/wav$LF",
    $fileEnc,
    "--$boundary--$LF"
) -join $LF

try {
    $response = Invoke-RestMethod -Uri "$API_URL/api/v1/transcribe" -Method Post -ContentType "multipart/form-data; boundary=`"$boundary`"" -Body $bodyLines
    
    Write-Host "✓ Upload successful!" -ForegroundColor Green
    $jobId = $response.job_id
    Write-Host "Job ID: $jobId" -ForegroundColor Cyan
    Write-Host ""
    
    # Monitor status
    Write-Host "Monitoring job progress..." -ForegroundColor Yellow
    for ($i = 0; $i -lt 120; $i++) {
        Start-Sleep -Seconds 3
        $status = Invoke-RestMethod -Uri "$API_URL/api/v1/status/$jobId"
        
        $progressBar = "=" * [Math]::Floor($status.progress / 2)
        Write-Host "[$($status.status)] $progressBar $($status.progress)% - $($status.message)" -ForegroundColor Gray
        
        if ($status.status -eq "completed") {
            Write-Host ""
            Write-Host "🎉 SUCCESS! Pipeline completed!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Results:" -ForegroundColor Cyan
            Write-Host "  Separated audio: $($status.result.separated_audio_path)" -ForegroundColor White
            Write-Host "  MIDI file: $($status.result.midi_path)" -ForegroundColor White
            Write-Host "  MusicXML file: $($status.result.musicxml_path)" -ForegroundColor White
            Write-Host ""
            Write-Host "✓ You can now upload MP3/MP4 files and get MusicXML! 🎵📄" -ForegroundColor Green
            break
        }
        
        if ($status.status -eq "failed") {
            Write-Host ""
            Write-Host "✗ Job failed: $($status.error)" -ForegroundColor Red
            break
        }
    }
} catch {
    Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host $_.Exception | Format-List -Force
}
