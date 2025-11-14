#!/bin/bash

# Test Full Microservices System with Real MP3
# Tests the cleaned system end-to-end: API + Worker + Pub/Sub
# Usage: ./test-full-system.sh [path/to/audio.mp3]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Configuration
TEST_MP3="${1:-/Users/jiawen/Documents/GitHub/groovesheet/demucus/input/nevergonnagiveyouup.MP3}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_URL="http://localhost:8080"

cd "$PROJECT_ROOT"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Testing Full Microservices System${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check if test MP3 exists
if [ ! -f "$TEST_MP3" ]; then
    echo -e "${RED}❌ Test MP3 not found: $TEST_MP3${NC}"
    echo -e "${YELLOW}Please ensure the test file exists${NC}"
    exit 1
fi

# Get file info
FILE_NAME=$(basename "$TEST_MP3")
FILE_SIZE=$(du -h "$TEST_MP3" | cut -f1)

echo -e "${GREEN}🎵 Test file: $FILE_NAME${NC}"
echo -e "${GRAY}📁 Size: $FILE_SIZE${NC}"
echo ""

# Step 1: Start the microservices system
echo -e "${YELLOW}Step 1: Starting microservices system (LOCAL MODE)...${NC}"
echo -e "${GRAY}Stopping any existing containers...${NC}"
docker-compose -f docker-compose.local.yml down > /dev/null 2>&1 || true

# Clean old jobs (keep uploads folder if present)
echo -e "${GRAY}Cleaning previous local jobs...${NC}"
if [ -d "$PROJECT_ROOT/testing/local-jobs" ]; then
    find "$PROJECT_ROOT/testing/local-jobs" -mindepth 1 -maxdepth 1 ! -name 'uploads' -exec rm -rf {} + 2>/dev/null || true
fi

echo -e "${GRAY}Building and starting services...${NC}"
if ! docker-compose -f docker-compose.local.yml up --build -d > /dev/null 2>&1; then
    echo -e "${RED}❌ Failed to start microservices${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Services started${NC}"
echo ""

# Step 2: Wait for services to be ready
echo -e "${YELLOW}Step 2: Waiting for services to be ready...${NC}"
echo -e "${GRAY}Checking API health...${NC}"

maxRetries=10
retryCount=0
apiReady=false

while [ $retryCount -lt $maxRetries ] && [ "$apiReady" = false ]; do
    if response=$(curl -s -f -m 5 "$API_URL/health" 2>/dev/null); then
        if echo "$response" | grep -q "healthy\|OK" || [ "$response" = "OK" ]; then
            apiReady=true
            echo -e "${GREEN}✅ API service is ready${NC}"
        fi
    fi
    
    if [ "$apiReady" = false ]; then
        retryCount=$((retryCount + 1))
        echo -e "${GRAY}  Attempt $retryCount/$maxRetries - waiting...${NC}"
        sleep 3
    fi
done

if [ "$apiReady" = false ]; then
    echo -e "${RED}❌ API service failed to become ready${NC}"
    echo -e "${YELLOW}Checking logs...${NC}"
    docker-compose -f docker-compose.local.yml logs api
    exit 1
fi

# Check worker container status
echo -e "${GRAY}Checking worker status...${NC}"
workerStatus=$(docker-compose -f docker-compose.local.yml ps worker --format "{{.Status}}" 2>/dev/null || echo "unknown")
echo -e "${GRAY}  Worker status: $workerStatus${NC}"
echo ""

# Step 3: Submit job to API
echo -e "${YELLOW}Step 3: Submitting transcription job...${NC}"

# Use curl for multipart upload (works on Mac/Linux)
if ! response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Authorization: Bearer test-token-for-local-testing" \
    -F "file=@$TEST_MP3" \
    "$API_URL/api/v1/transcribe" 2>/dev/null); then
    echo -e "${RED}❌ Failed to submit job${NC}"
    echo -e "${YELLOW}Checking API logs...${NC}"
    docker-compose -f docker-compose.local.yml logs api
    exit 1
fi

# Extract HTTP status code and body
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" -lt 200 ] || [ "$http_code" -ge 300 ]; then
    echo -e "${RED}❌ Upload failed: HTTP $http_code${NC}"
    echo -e "${YELLOW}Response: $body${NC}"
    echo -e "${YELLOW}Checking API logs...${NC}"
    docker-compose -f docker-compose.local.yml logs api
    exit 1
fi

# Extract job_id from JSON response
jobId=$(echo "$body" | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$jobId" ]; then
    echo -e "${RED}❌ Failed to extract job_id from response${NC}"
    echo -e "${YELLOW}Response: $body${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Job submitted successfully${NC}"
echo -e "${CYAN}  Job ID: $jobId${NC}"
echo ""

# Step 4: Monitor job progress
echo -e "${YELLOW}Step 4: Monitoring job progress...${NC}"
echo -e "${GRAY}This may take 2-3 minutes for the full transcription${NC}"
echo ""

maxWaitMinutes=10
startTime=$(date +%s)
lastProgress=-1
status=""

while true; do
    # Get status
    if statusResponse=$(curl -s -f -m 10 "$API_URL/api/v1/status/$jobId" 2>/dev/null); then
        elapsed=$(echo "scale=1; ($(date +%s) - $startTime) / 60" | bc)
        progress=$(echo "$statusResponse" | grep -o '"progress":[0-9]*' | cut -d':' -f2 || echo "0")
        status=$(echo "$statusResponse" | grep -o '"status":"[^"]*' | cut -d'"' -f4 || echo "unknown")
        
        # Only show progress updates when they change
        if [ "$progress" != "$lastProgress" ]; then
            echo -e "  [${elapsed} min] Status: $status | Progress: ${progress}%"
            lastProgress=$progress
        fi
        
        # Check if completed
        if [ "$status" = "completed" ]; then
            echo ""
            echo -e "${GREEN}✅ Transcription completed successfully!${NC}"
            echo -e "${CYAN}  Total time: ${elapsed} minutes${NC}"
            echo -e "${CYAN}  Final progress: ${progress}%${NC}"
            
            # Show download URL if available
            downloadUrl=$(echo "$statusResponse" | grep -o '"download_url":"[^"]*' | cut -d'"' -f4 || echo "")
            if [ -n "$downloadUrl" ]; then
                echo -e "${GRAY}  Download URL: $downloadUrl${NC}"
            fi
            
            break
        fi
        
        # Check if failed
        if [ "$status" = "failed" ]; then
            echo ""
            echo -e "${RED}❌ Job failed${NC}"
            echo -e "${YELLOW}Response: $statusResponse${NC}"
            break
        fi
        
        # Check timeout
        if (( $(echo "$elapsed > $maxWaitMinutes" | bc -l) )); then
            echo ""
            echo -e "${RED}❌ Job timed out after $maxWaitMinutes minutes${NC}"
            echo -e "${YELLOW}Last status: $status ($progress%)${NC}"
            break
        fi
        
        sleep 5
    else
        echo -e "  ${RED}Error checking status${NC}"
        sleep 10
    fi
done

echo ""

# Step 5: Show logs for debugging
echo -e "${YELLOW}Step 5: System logs (last 20 lines each)...${NC}"
echo ""

echo -e "${CYAN}API Logs:${NC}"
echo -e "${GRAY}----------------------------------------${NC}"
docker-compose -f docker-compose.local.yml logs --tail=20 api

echo ""
echo -e "${CYAN}Worker Logs:${NC}"
echo -e "${GRAY}----------------------------------------${NC}"
docker-compose -f docker-compose.local.yml logs --tail=20 worker

echo ""

# Step 6: Test download if job completed successfully
if [ "$status" = "completed" ] && [ -n "$downloadUrl" ]; then
    echo -e "${YELLOW}Step 6: Testing download...${NC}"
    
    timestamp=$(date +%Y%m%d_%H%M%S)
    downloadPath="$PROJECT_ROOT/test_output_${timestamp}.musicxml"
    
    if curl -s -f -m 30 -o "$downloadPath" "$downloadUrl" 2>/dev/null; then
        if [ -f "$downloadPath" ]; then
            fileSize=$(du -h "$downloadPath" | cut -f1)
            echo -e "${GREEN}✅ Download successful${NC}"
            echo -e "${CYAN}  File: $downloadPath${NC}"
            echo -e "${GRAY}  Size: $fileSize${NC}"
        fi
    else
        echo -e "${RED}❌ Download failed${NC}"
    fi
fi

echo ""
echo -e "${CYAN}========================================${NC}"

if [ "$status" = "completed" ]; then
    echo -e "${GREEN}  ✅ FULL SYSTEM TEST PASSED${NC}"
    echo -e "${GREEN}  All microservices working correctly!${NC}"
else
    echo -e "${RED}  ❌ FULL SYSTEM TEST FAILED${NC}"
    echo -e "${YELLOW}  Check logs above for details${NC}"
fi

echo -e "${CYAN}========================================${NC}"
echo ""

# Cleanup option
read -p "Stop containers? (y/n): " cleanup
if [ "$cleanup" = "y" ] || [ "$cleanup" = "Y" ]; then
    echo -e "${GRAY}Stopping containers...${NC}"
    docker-compose -f docker-compose.local.yml down
    echo -e "${GREEN}✅ Containers stopped${NC}"
fi

