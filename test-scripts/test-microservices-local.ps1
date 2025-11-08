#!/usr/bin/env pwsh
# Test microservices locally

Write-Host "=== Building API Service ===" -ForegroundColor Cyan
docker build -t groovesheet-api:local ./api-service

if ($LASTEXITCODE -ne 0) {
    Write-Host "API build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Building Worker Service ===" -ForegroundColor Cyan
docker build -t groovesheet-worker:local ./worker-service

if ($LASTEXITCODE -ne 0) {
    Write-Host "Worker build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Starting services with docker-compose ===" -ForegroundColor Cyan
docker-compose -f docker-compose.microservices.yml up

Write-Host "`nServices started! API should be at http://localhost:8000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
