# 🐳 Docker Quick Start for macOS

Having trouble with `setup.py` and dependency installation? Use Docker instead!

## Prerequisites

1. **Install Docker Desktop for Mac**
   - Download: https://www.docker.com/products/docker-desktop
   - Install and start Docker Desktop
   - Verify: You should see the Docker icon in your menu bar

## Three Ways to Start

### Option 1: Automated Script (Recommended)
```bash
# Clone the repo
git clone https://github.com/EdwardZehuaZhang/drumscore-be.git
cd drumscore-be

# Make script executable and run
chmod +x start-docker.sh
./start-docker.sh
```

The script will automatically:
- ✅ Check Docker installation
- ✅ Verify Docker is running
- ✅ Create necessary directories
- ✅ Build the Docker image
- ✅ Start the container
- ✅ Wait for the service to be ready
- ✅ Open API docs in your browser

**Wait 5-10 minutes** for the first build, then you're ready!

### Option 2: Docker Compose (Manual)
```bash
# Clone the repo
git clone https://github.com/EdwardZehuaZhang/drumscore-be.git
cd drumscore-be

# Create directories
mkdir -p backend/uploads backend/outputs backend/logs backend/temp

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Wait for "Application startup complete" message
```

### Option 3: Docker Build (Advanced)
```bash
# Build image
docker build -t drumscore-backend .

# Run container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/backend/uploads:/app/backend/uploads \
  -v $(pwd)/backend/outputs:/app/backend/outputs \
  -v $(pwd)/backend/logs:/app/backend/logs \
  --name drumscore-backend \
  drumscore-backend
```

## Verify It's Working

Once started, test the API:

```bash
# Check health
curl http://localhost:8000/api/health

# Should return:
# {"status":"healthy","model_exists":true}
```

**Open in browser:**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/health

## Useful Commands

```bash
# View logs in real-time
docker-compose logs -f

# Stop the service
docker-compose down

# Restart the service
docker-compose restart

# Access container shell
docker-compose exec drumscore-backend bash

# Rebuild after code changes
docker-compose build --no-cache
docker-compose up -d

# Check container status
docker-compose ps

# View resource usage
docker stats drumscore-backend
```

## Your Files

All your data is accessible on your Mac:
- **Uploads**: `backend/uploads/`
- **Outputs**: `backend/outputs/`
- **Logs**: `backend/logs/`

Files persist even when you stop/restart the container.

## Troubleshooting

### "Cannot connect to Docker daemon"
→ Start Docker Desktop from Applications

### Port 8000 already in use
```bash
# Edit docker-compose.yml, change:
ports:
  - "8001:8000"  # Use port 8001 instead
```

### Container keeps restarting
```bash
# Check logs
docker-compose logs -f drumscore-backend
```

### Out of disk space
```bash
# Clean up Docker
docker system prune -a
```

### Slow build on Apple Silicon (M1/M2/M3)
```bash
# Add to docker-compose.yml:
services:
  drumscore-backend:
    platform: linux/arm64
    # ... rest of config
```

## Why Docker?

Docker eliminates:
- ❌ Python version issues
- ❌ Dependency installation failures
- ❌ Cython compilation errors
- ❌ System package problems
- ❌ "Works on my machine" syndrome

You get:
- ✅ One-command setup
- ✅ Guaranteed to work
- ✅ Same environment everywhere
- ✅ Easy updates
- ✅ No system pollution

## Need More Help?

- **Quick guide**: See `DOCKER_QUICKSTART.md`
- **Detailed docs**: See `DOCKER_SETUP.md`
- **Summary**: See `DOCKER_SUMMARY.md`

---

**TL;DR for macOS:**
```bash
# Install Docker Desktop, then:
git clone https://github.com/EdwardZehuaZhang/drumscore-be.git
cd drumscore-be
chmod +x start-docker.sh
./start-docker.sh
# Wait 5-10 minutes, then open http://localhost:8000/docs
```

🎉 **That's it! No more dependency issues!**
