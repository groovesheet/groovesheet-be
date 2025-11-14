# Worker service Dockerfile - cleaned version (no backend dependency)
FROM python:3.8-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    ffmpeg \
    git \
    pkg-config \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from parent context
COPY annoteator-worker/requirements.txt .

# Install Python packages in critical order for TensorFlow 2.10.0
RUN pip install --upgrade pip 'setuptools<60' wheel
RUN pip install 'Cython>=0.29.24'
RUN pip install 'numpy==1.24.0'
RUN pip install 'protobuf==3.19.6'

# Install old compatible google-cloud packages  
RUN pip install --no-deps 'google-cloud-storage==1.42.3' 'google-cloud-pubsub==2.8.0'
RUN pip install 'google-api-core<2.0' 'google-auth<2.0' 'googleapis-common-protos<2.0'

# Install other requirements (numpy already pinned, so it won't be upgraded)
RUN pip install --no-cache-dir --default-timeout=300 --upgrade-strategy only-if-needed -r requirements.txt

# Copy ML libraries from lib directory
COPY lib/AnNOTEator /app/lib/AnNOTEator

# Note: demucs==3.0.4 is installed via requirements.txt (from PyPI)
# The demucs models are stored in lib/AnNOTEator/inference/pretrained_models/demucs/

# Copy worker service files
COPY annoteator-worker/worker.py .
COPY annoteator-worker/services/ /app/services/

# Set PYTHONPATH for ML libraries only (no backend)
ENV PYTHONPATH=/app:/app/lib/AnNOTEator

# Force unbuffered output for real-time logs
ENV PYTHONUNBUFFERED=1

# Set protobuf implementation (critical for TensorFlow 2.10.0)
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

EXPOSE 8080

# Run worker (cloud version by default, local version for testing)
CMD ["python", "-u", "worker.py"]
