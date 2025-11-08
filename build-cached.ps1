# Docker BuildKit cache configuration
# This preserves build cache across rebuilds

# Enable BuildKit for faster builds with better caching
$env:DOCKER_BUILDKIT=1
$env:COMPOSE_DOCKER_CLI_BUILD=1

Write-Host "Building with BuildKit cache enabled..." -ForegroundColor Cyan

# Build with cache mount (much faster on subsequent builds)
docker build `
  --platform linux/amd64 `
  --cache-from groovesheet-be-test:latest `
  --build-arg BUILDKIT_INLINE_CACHE=1 `
  -t groovesheet-be-test:latest `
  -f Dockerfile .

Write-Host "Build complete! Cache preserved for next build." -ForegroundColor Green
