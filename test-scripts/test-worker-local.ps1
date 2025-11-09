# Test Worker Processing Locally
# This tests the exact worker pipeline without Docker/Cloud

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Testing Worker Processing Locally" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set up environment
$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION = "python"
$env:TF_CPP_MIN_LOG_LEVEL = "3"

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "  $pythonVersion" -ForegroundColor White

if ($pythonVersion -notmatch "Python 3\.8") {
    Write-Host "  ⚠️  Warning: Worker requires Python 3.8" -ForegroundColor Red
}

Write-Host ""
Write-Host "Setting up paths..." -ForegroundColor Yellow
$scriptDir = Split-Path -Parent $PSCommandPath
$projectRoot = Split-Path -Parent $scriptDir
$testScript = Join-Path $scriptDir "test_worker_processing.py"

Write-Host "  Project: $projectRoot" -ForegroundColor Gray
Write-Host "  Test script: $testScript" -ForegroundColor Gray

# Check for test audio
$testAudio = Join-Path $projectRoot "Nirvana - Smells Like Teen Spirit (Official Music Video).mp3"

if (!(Test-Path $testAudio)) {
    Write-Host ""
    Write-Host "⚠️  Test audio not found: $testAudio" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please provide an audio file:" -ForegroundColor Yellow
    Write-Host "  python test_worker_processing.py <path_to_audio.mp3>" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "Running worker processing test..." -ForegroundColor Yellow
Write-Host "This will take 5-10 minutes for a full song" -ForegroundColor Gray
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor DarkGray

# Run the test
Set-Location $projectRoot
python $testScript $testAudio

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✓ Worker Test PASSED" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Check output in: $projectRoot\test_output" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  ❌ Worker Test FAILED" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Review the error messages above" -ForegroundColor White
}

Write-Host ""
