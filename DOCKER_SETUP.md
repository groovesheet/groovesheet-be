# Docker Setup Guide for DrumScore Backend

## Prerequisites

### On macOS:
```bash
# Install Docker Desktop for Mac
# Download from: https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
docker-compose --version
```

### On Windows:
```powershell
# Install Docker Desktop for Windows
# Download from: https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
docker-compose --version
```

### On Linux:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/EdwardZehuaZhang/drumscore-be.git
cd drumscore-be
```

### 2. Set Up Environment File
```bash
# Copy example env file
cp backend/.env.example backend/.env

# Edit the .env file if needed (optional)
nano backend/.env  # or use your favorite editor
```

### 3. Build and Run with Docker Compose
```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Wait for "Application startup complete" message
```

### 4. Verify It's Running
```bash
# Check container status
docker-compose ps

# Test the API
curl http://localhost:8000/api/health

# Or open in browser:
open http://localhost:8000/docs  # macOS
# or
start http://localhost:8000/docs  # Windows
```

## Docker Commands

### Basic Operations
```bash
# Start the service
docker-compose up -d

# Stop the service
docker-compose down

# Restart the service
docker-compose restart

# View logs
docker-compose logs -f drumscore-backend

# View last 100 lines of logs
docker-compose logs --tail=100 drumscore-backend
```

### Building and Updating
```bash
# Rebuild the image after code changes
docker-compose build

# Rebuild without cache (fresh build)
docker-compose build --no-cache

# Pull latest changes and rebuild
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

### Debugging
```bash
# Execute commands inside the container
docker-compose exec drumscore-backend bash

# Check Python packages
docker-compose exec drumscore-backend pip list

# Check disk space
docker-compose exec drumscore-backend df -h

# View container resource usage
docker stats drumscore-backend
```

### Cleanup
```bash
# Remove stopped containers
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Remove all unused Docker resources
docker system prune -a
```

## Volume Management

The Docker setup uses volumes to persist data:

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `./backend/uploads` | `/app/backend/uploads` | Uploaded audio files |
| `./backend/outputs` | `/app/backend/outputs` | Generated MusicXML files |
| `./backend/logs` | `/app/backend/logs` | Application logs |
| `./backend/.env` | `/app/backend/.env` | Configuration |
| `./AnNOTEator/inference/pretrained_models` | `/app/AnNOTEator/inference/pretrained_models` | Model files |

### Backing Up Data
```bash
# Backup outputs
tar -czf drumscore-outputs-$(date +%Y%m%d).tar.gz backend/outputs/

# Backup logs
tar -czf drumscore-logs-$(date +%Y%m%d).tar.gz backend/logs/
```

## Configuration

### Environment Variables

Edit `backend/.env` to configure:

```bash
# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Processing settings
DEMUCS_DEVICE=cpu  # or 'cuda' for GPU
OMNIZART_DEVICE=cpu  # or 'cuda' for GPU

# Directory settings
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
LOG_LEVEL=INFO
```

### Resource Limits

To limit Docker resource usage, add to `docker-compose.yml`:

```yaml
services:
  drumscore-backend:
    # ... existing config ...
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
```

## Troubleshooting

### Issue: "Cannot connect to Docker daemon"
```bash
# Start Docker Desktop (macOS/Windows)
# Or start Docker service (Linux):
sudo systemctl start docker
```

### Issue: Port 8000 already in use
```bash
# Find what's using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Either stop that process or change the port in docker-compose.yml:
ports:
  - "8001:8000"  # Use port 8001 on host
```

### Issue: Container crashes on startup
```bash
# View detailed logs
docker-compose logs drumscore-backend

# Check if model files exist
ls -lh AnNOTEator/inference/pretrained_models/

# Rebuild without cache
docker-compose build --no-cache
docker-compose up -d
```

### Issue: Out of memory
```bash
# Check Docker memory settings in Docker Desktop
# Increase memory limit to at least 4GB

# Or add swap space (Linux)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Issue: Build fails on macOS M1/M2
```bash
# Use platform flag
docker-compose build --build-arg BUILDPLATFORM=linux/arm64

# Or add to docker-compose.yml:
services:
  drumscore-backend:
    platform: linux/arm64
```

## Performance Tips

### 1. Use BuildKit for Faster Builds
```bash
export DOCKER_BUILDKIT=1
docker-compose build
```

### 2. Prune Unused Images Regularly
```bash
docker image prune -a
```

### 3. Use Multi-Stage Builds
The provided Dockerfile already uses multi-stage builds to keep the final image small.

### 4. Monitor Resource Usage
```bash
# Real-time monitoring
docker stats drumscore-backend

# Check container size
docker-compose images
```

## Production Deployment

For production deployment, consider:

1. **Use a reverse proxy** (nginx, traefik)
2. **Enable HTTPS** with Let's Encrypt
3. **Set up logging** with proper log rotation
4. **Configure backups** for volumes
5. **Use secrets management** for sensitive data
6. **Set up monitoring** (Prometheus, Grafana)
7. **Configure auto-restart** policies

Example with nginx reverse proxy:

```yaml
# docker-compose.prod.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - drumscore-backend

  drumscore-backend:
    # Remove port exposure (nginx handles it)
    # ports:
    #   - "8000:8000"
    expose:
      - "8000"
```

## Testing the Docker Setup

```bash
# 1. Build and start
docker-compose up -d

# 2. Wait for startup (check logs)
docker-compose logs -f

# 3. Test health endpoint
curl http://localhost:8000/api/health

# 4. Test transcription (if you have test_simple.py)
python test_simple.py

# 5. Check generated files
ls -lh backend/outputs/
```

## Support

If you encounter issues:
1. Check the logs: `docker-compose logs -f`
2. Verify model files exist in `AnNOTEator/inference/pretrained_models/`
3. Ensure Docker has enough resources (4GB+ RAM)
4. Try rebuilding without cache: `docker-compose build --no-cache`

For more help, open an issue on GitHub.
