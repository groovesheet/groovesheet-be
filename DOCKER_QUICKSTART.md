# DrumScore Backend - Quick Start with Docker 🐳

**For macOS Users (Your Friend)**

This guide will help you set up and run the DrumScore backend using Docker, avoiding all the dependency installation issues!

## Prerequisites

1. **Install Docker Desktop for Mac**
   - Download from: https://www.docker.com/products/docker-desktop
   - Install and start Docker Desktop
   - Verify it's running (you should see the Docker icon in your menu bar)

## Quick Start (3 Easy Steps!)

### Step 1: Clone the Repository
```bash
git clone https://github.com/EdwardZehuaZhang/drumscore-be.git
cd drumscore-be
```

### Step 2: Run the Setup Script
```bash
# Make the script executable
chmod +x start-docker.sh

# Run it!
./start-docker.sh
```

That's it! The script will:
- ✅ Check if Docker is installed and running
- ✅ Check for model files
- ✅ Create necessary directories
- ✅ Build the Docker container (this takes 5-10 minutes the first time)
- ✅ Start the service
- ✅ Wait for it to be ready
- ✅ Open the API documentation in your browser

### Step 3: Test It!

Once the script completes, your browser should automatically open to `http://localhost:8000/docs`

You can also test the API:
```bash
# Check health
curl http://localhost:8000/api/health

# You should see something like:
# {"status":"healthy","model_exists":true}
```

## Manual Method (Alternative)

If you prefer to run commands manually:

```bash
# 1. Create directories
mkdir -p backend/uploads backend/outputs backend/logs backend/temp

# 2. Build and start
docker-compose up -d

# 3. View logs
docker-compose logs -f

# 4. Wait for "Application startup complete" message

# 5. Test
curl http://localhost:8000/api/health
```

## Useful Commands

```bash
# View logs in real-time
docker-compose logs -f

# Stop the service
docker-compose down

# Restart the service
docker-compose restart

# Access container shell (for debugging)
docker-compose exec drumscore-backend bash

# Rebuild after code changes
docker-compose build --no-cache
docker-compose up -d

# Check container status
docker-compose ps

# See resource usage
docker stats drumscore-backend
```

## Troubleshooting

### Problem: "Cannot connect to the Docker daemon"
**Solution:** Start Docker Desktop from your Applications folder

### Problem: Port 8000 already in use
**Solution:** Either stop the other service using port 8000, or change the port:
```bash
# Edit docker-compose.yml, change the ports line to:
ports:
  - "8001:8000"  # Use port 8001 instead
```

### Problem: Container keeps restarting
**Solution:** Check the logs:
```bash
docker-compose logs -f drumscore-backend
```

### Problem: Out of disk space
**Solution:** Clean up Docker:
```bash
docker system prune -a
```

### Problem: Build is very slow
**Solution:** This is normal on first build (5-10 minutes). Docker caches layers, so subsequent builds are much faster (1-2 minutes).

## What's Happening Inside?

The Docker container:
1. Uses Python 3.8 (same as your working environment)
2. Installs all dependencies in the correct order (Cython → NumPy → ML frameworks → rest)
3. Includes all necessary system packages (FFmpeg, build tools, etc.)
4. Mounts your local directories for uploads/outputs/logs
5. Runs the FastAPI server on port 8000

## Performance Tips

### For macOS with Apple Silicon (M1/M2/M3)
The container uses x86_64 architecture by default. For better performance, you can build for ARM:

```bash
# Edit docker-compose.yml and add:
services:
  drumscore-backend:
    platform: linux/arm64
    # ... rest of config
```

### Resource Limits
The docker-compose.yml is configured to use:
- Max 4 CPU cores
- Max 8GB RAM
- Min 2 CPU cores
- Min 4GB RAM

Adjust these in `docker-compose.yml` if needed.

## File Locations

Your files are accessible both inside and outside the container:

| Host Location | Container Location | Purpose |
|---------------|-------------------|---------|
| `backend/uploads/` | `/app/backend/uploads/` | Uploaded audio files |
| `backend/outputs/` | `/app/backend/outputs/` | Generated MusicXML files |
| `backend/logs/` | `/app/backend/logs/` | Application logs |
| `backend/temp/` | `/app/backend/temp/` | Temporary files |

You can access these directories normally on your Mac!

## API Endpoints

Once running, you can access:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **Transcription**: POST to http://localhost:8000/api/transcribe

## Next Steps

1. Try uploading an audio file through the API docs at http://localhost:8000/docs
2. Check the output in `backend/outputs/`
3. View logs if needed: `docker-compose logs -f`

## For Windows Users

Windows users can use the PowerShell script:
```powershell
.\start-docker.ps1
```

## Getting Help

If you encounter issues:
1. Check logs: `docker-compose logs -f`
2. Verify Docker is running: `docker info`
3. Check disk space: `docker system df`
4. Try rebuilding: `docker-compose build --no-cache`

## Why Docker?

Docker solves:
- ✅ "Works on my machine" problems
- ✅ Complex dependency installation order
- ✅ System package requirements (FFmpeg, build tools, etc.)
- ✅ Python version compatibility
- ✅ Cython compilation issues
- ✅ Different OS behaviors (Windows vs macOS vs Linux)

Everything just works! 🎉
