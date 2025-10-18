#!/bin/bash

# DrumScore Backend - Quick Start Script for macOS
# This script helps set up and run the backend using Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  DrumScore Backend - Docker Setup  ${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# Check if Docker is installed
echo -e "${YELLOW}[1/6] Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    echo -e "${YELLOW}Please install Docker Desktop for Mac from: https://www.docker.com/products/docker-desktop${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed!${NC}"
    echo -e "${YELLOW}Please install Docker Desktop for Mac (includes Docker Compose)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker installed: $(docker --version)${NC}"
echo -e "${GREEN}✓ Docker Compose installed: $(docker-compose --version)${NC}"
echo ""

# Check if Docker is running
echo -e "${YELLOW}[2/6] Checking if Docker is running...${NC}"
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running!${NC}"
    echo -e "${YELLOW}Please start Docker Desktop and try again.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Check if model files exist
echo -e "${YELLOW}[3/6] Checking for model files...${NC}"
MODEL_DIR="AnNOTEator/inference/pretrained_models"
if [ ! -d "$MODEL_DIR" ] || [ -z "$(ls -A $MODEL_DIR 2>/dev/null)" ]; then
    echo -e "${RED}❌ Model files not found in $MODEL_DIR${NC}"
    echo -e "${YELLOW}Please ensure AnNOTEator model files are downloaded.${NC}"
    echo -e "${YELLOW}The container may download them on first use.${NC}"
else
    echo -e "${GREEN}✓ Model files found${NC}"
fi
echo ""

# Create necessary directories
echo -e "${YELLOW}[4/6] Creating necessary directories...${NC}"
mkdir -p backend/uploads backend/outputs backend/logs backend/temp
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Check if container is already running
echo -e "${YELLOW}[5/6] Checking existing containers...${NC}"
if docker ps -a | grep -q drumscore-backend; then
    echo -e "${YELLOW}Found existing container. Removing it...${NC}"
    docker-compose down
    echo -e "${GREEN}✓ Old container removed${NC}"
fi
echo ""

# Build and start the container
echo -e "${YELLOW}[6/6] Building and starting Docker container...${NC}"
echo -e "${BLUE}This may take 5-10 minutes on first build...${NC}"
echo ""

docker-compose build --no-cache
docker-compose up -d

echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  Container started successfully!    ${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

# Wait for the service to be ready
echo -e "${YELLOW}Waiting for service to be ready...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Service is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT + 1))
done
echo ""

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Service failed to start within expected time${NC}"
    echo -e "${YELLOW}Check logs with: docker-compose logs -f${NC}"
    exit 1
fi

# Display useful information
echo ""
echo -e "${BLUE}=====================================${NC}"
echo -e "${GREEN}Service Information:${NC}"
echo -e "${BLUE}=====================================${NC}"
echo -e "API Endpoint: ${GREEN}http://localhost:8000${NC}"
echo -e "API Docs: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "Health Check: ${GREEN}http://localhost:8000/api/health${NC}"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo -e "  View logs:       ${YELLOW}docker-compose logs -f${NC}"
echo -e "  Stop service:    ${YELLOW}docker-compose down${NC}"
echo -e "  Restart service: ${YELLOW}docker-compose restart${NC}"
echo -e "  Shell access:    ${YELLOW}docker-compose exec drumscore-backend bash${NC}"
echo ""
echo -e "${GREEN}Opening API documentation in browser...${NC}"
sleep 2
open http://localhost:8000/docs

echo ""
echo -e "${GREEN}Setup complete! 🎉${NC}"
