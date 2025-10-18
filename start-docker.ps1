# DrumScore Backend - Quick Start Script for Windows PowerShell
# This script helps set up and run the backend using Docker

Write-Host "=====================================" -ForegroundColor Blue
Write-Host "  DrumScore Backend - Docker Setup  " -ForegroundColor Blue
Write-Host "=====================================" -ForegroundColor Blue
Write-Host ""

# Check if Docker is installed
Write-Host "[1/6] Checking Docker installation..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    $composeVersion = docker-compose --version
    Write-Host "✓ Docker installed: $dockerVersion" -ForegroundColor Green
    Write-Host "✓ Docker Compose installed: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not installed!" -ForegroundColor Red
    Write-Host "Please install Docker Desktop for Windows from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Check if Docker is running
Write-Host "[2/6] Checking if Docker is running..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Check if model files exist
Write-Host "[3/6] Checking for model files..." -ForegroundColor Yellow
$modelDir = "AnNOTEator\inference\pretrained_models"
if (!(Test-Path $modelDir) -or !(Get-ChildItem $modelDir -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Model files not found in $modelDir" -ForegroundColor Red
    Write-Host "Please ensure AnNOTEator model files are downloaded." -ForegroundColor Yellow
    Write-Host "The container may download them on first use." -ForegroundColor Yellow
} else {
    Write-Host "✓ Model files found" -ForegroundColor Green
}
Write-Host ""

# Create necessary directories
Write-Host "[4/6] Creating necessary directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "backend\uploads" | Out-Null
New-Item -ItemType Directory -Force -Path "backend\outputs" | Out-Null
New-Item -ItemType Directory -Force -Path "backend\logs" | Out-Null
New-Item -ItemType Directory -Force -Path "backend\temp" | Out-Null
Write-Host "✓ Directories created" -ForegroundColor Green
Write-Host ""

# Check if container is already running
Write-Host "[5/6] Checking existing containers..." -ForegroundColor Yellow
$existingContainer = docker ps -a --filter "name=drumscore-backend" --format "{{.Names}}"
if ($existingContainer) {
    Write-Host "Found existing container. Removing it..." -ForegroundColor Yellow
    docker-compose down
    Write-Host "✓ Old container removed" -ForegroundColor Green
}
Write-Host ""

# Build and start the container
Write-Host "[6/6] Building and starting Docker container..." -ForegroundColor Yellow
Write-Host "This may take 5-10 minutes on first build..." -ForegroundColor Blue
Write-Host ""

docker-compose build --no-cache
docker-compose up -d

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  Container started successfully!    " -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""

# Wait for the service to be ready
Write-Host "Waiting for service to be ready..." -ForegroundColor Yellow
$maxRetries = 30
$retryCount = 0
while ($retryCount -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ Service is ready!" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 2
        $retryCount++
    }
}
Write-Host ""

if ($retryCount -eq $maxRetries) {
    Write-Host "❌ Service failed to start within expected time" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose logs -f" -ForegroundColor Yellow
    exit 1
}

# Display useful information
Write-Host ""
Write-Host "=====================================" -ForegroundColor Blue
Write-Host "Service Information:" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Blue
Write-Host "API Endpoint: http://localhost:8000" -ForegroundColor Green
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "Health Check: http://localhost:8000/api/health" -ForegroundColor Green
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Blue
Write-Host "  View logs:       docker-compose logs -f" -ForegroundColor Yellow
Write-Host "  Stop service:    docker-compose down" -ForegroundColor Yellow
Write-Host "  Restart service: docker-compose restart" -ForegroundColor Yellow
Write-Host "  Shell access:    docker-compose exec drumscore-backend bash" -ForegroundColor Yellow
Write-Host ""
Write-Host "Opening API documentation in browser..." -ForegroundColor Green
Start-Sleep -Seconds 2
Start-Process "http://localhost:8000/docs"

Write-Host ""
Write-Host "Setup complete! 🎉" -ForegroundColor Green
