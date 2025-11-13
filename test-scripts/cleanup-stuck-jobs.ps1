#!/usr/bin/env pwsh
# Clean up stuck jobs in GCS that are marked as "processing" but never completed

$ErrorActionPreference = "Stop"

$BUCKET = "groovesheet-jobs"
$PROJECT = "groovesheet2025"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Clean Up Stuck Jobs" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# List of known stuck job IDs from logs
$STUCK_JOBS = @(
    "3641cab3-24b4-4226-85fd-9d08ad1be8b4",
    "1c5052d4-00cb-490a-926c-a26be22124a8",
    "b04536bc-a59d-40b2-9fda-c5ff6452e166",
    "71125b87-8973-4ddb-a138-5ec90aebdff9"
)

Write-Host "Found $($STUCK_JOBS.Count) stuck jobs to clean up" -ForegroundColor Yellow
Write-Host ""

foreach ($job_id in $STUCK_JOBS) {
    Write-Host "Cleaning up job: $job_id" -ForegroundColor Cyan
    
    # Check if metadata exists
    $metadata_path = "gs://$BUCKET/jobs/$job_id/metadata.json"
    
    try {
        # Download current metadata
        $temp_file = [System.IO.Path]::GetTempFileName()
        gcloud storage cp $metadata_path $temp_file 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            # Update status to failed
            $metadata = Get-Content $temp_file | ConvertFrom-Json
            $metadata.status = "failed"
            $metadata.error = "Job timeout - cleaned up during queue purge"
            $metadata.updated_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            
            # Upload updated metadata
            $metadata | ConvertTo-Json -Depth 10 | Set-Content $temp_file
            gcloud storage cp $temp_file $metadata_path
            
            Write-Host "  ✓ Marked as failed" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ Metadata not found (already deleted?)" -ForegroundColor Yellow
        }
        
        Remove-Item $temp_file -Force -ErrorAction SilentlyContinue
        
    } catch {
        Write-Host "  ✗ Error: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✓ Cleanup Complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "All stuck jobs marked as failed." -ForegroundColor White
Write-Host "New job uploads will start fresh!" -ForegroundColor Cyan
