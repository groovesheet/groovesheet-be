# Force Linux AMD64 platform - required for TensorFlow 2.5.0 compatibility
# This ensures macOS users can build the image using TensorFlow Linux wheels
FROM --platform=linux/amd64 python:3.8-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools (required for compiling C extensions)
    build-essential \
    gcc \
    g++ \
    git \
    wget \
    # FFmpeg for audio processing
    ffmpeg \
    libsndfile1 \
    # For madmom and other audio libs
    libffi-dev \
    libssl-dev \
    # Clean up to reduce image size
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY backend/requirements.txt /app/backend/requirements.txt

# Install Python dependencies with proper order (matching setup.py)
# Step 1: Upgrade pip, setuptools, wheel
RUN pip install --upgrade pip setuptools wheel

# Step 2: Install Cython first (required for madmom compilation)
RUN pip install 'Cython>=0.29.24'

# Step 3: Install NumPy (required by TensorFlow 2.5.0 - MUST be 1.19.x)
RUN pip install 'numpy==1.19.5'

# Step 4: Install TensorFlow FIRST with compatible protobuf (3.20.x works on local machine)
RUN pip install 'tensorflow==2.5.0' 'protobuf>=3.20.0,<4.0'

# Step 5: Install remaining dependencies (excluding tensorflow and protobuf)
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Step 6: CRITICAL - Force upgrade typing-extensions after all other packages
RUN pip install --upgrade --force-reinstall 'typing-extensions>=4.8.0'

# Copy application code
COPY backend /app/backend
COPY AnNOTEator /app/AnNOTEator
COPY demucs /app/demucs
COPY omnizart /app/omnizart

# Install demucs and omnizart (if needed)
# Note: Most dependencies are already in requirements.txt
RUN cd /app/demucs && pip install -e . || echo "Demucs already available"
RUN cd /app/omnizart && pip install -e . || echo "Omnizart already available"

# CRITICAL: Re-fix protobuf after omnizart (it may downgrade)
RUN pip install --force-reinstall 'protobuf>=3.20.0,<4.0'

# CRITICAL: Re-upgrade typing-extensions after omnizart installation (omnizart downgrades it)
RUN pip install --upgrade --force-reinstall 'typing-extensions>=4.8.0'

# Create necessary directories
RUN mkdir -p /app/backend/uploads \
    /app/backend/temp \
    /app/backend/outputs \
    /app/backend/models \
    /app/backend/logs

# Set proper permissions
RUN chmod -R 755 /app

# Set PYTHONPATH to include all modules
ENV PYTHONPATH=/app:/app/backend:/app/AnNOTEator:/app/demucs:/app/omnizart:$PYTHONPATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=5)" || exit 1

# Set working directory to backend
WORKDIR /app/backend

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
