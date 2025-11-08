# Worker service Dockerfile
FROM python:3.8-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY worker-service/requirements.txt .

# Install Python packages
RUN pip install --upgrade pip setuptools wheel
RUN pip install 'Cython>=0.29.24'
RUN pip install 'numpy==1.19.5'
RUN pip install 'tensorflow==2.5.0' 'protobuf==3.9.2'

# Install old compatible google-cloud packages
RUN pip install --no-deps 'google-cloud-storage==1.42.3' 'google-cloud-pubsub==2.8.0'
RUN pip install 'google-api-core<2.0' 'google-auth<2.0' 'googleapis-common-protos<2.0'

# Install other requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend, ANoteator, and demucs from parent directory
# Note: Build context must be groovesheet-be/ directory, not worker-service/
# Note: We DON'T copy omnizart because AnNOTEatorService doesn't use it
COPY AnNOTEator /app/AnNOTEator
COPY demucs /app/demucs  
COPY backend /app/backend

# Install demucs from local copy
RUN cd /app/demucs && pip install -e .

# Copy worker code
COPY worker-service/worker.py .
COPY worker-service/worker_local.py .

# Set PYTHONPATH to include all modules (matching monolith)
ENV PYTHONPATH=/app:/app/backend:/app/AnNOTEator:/app/demucs:/app/omnizart:$PYTHONPATH

# Force unbuffered output so we can see logs in real-time
ENV PYTHONUNBUFFERED=1

# Set protobuf implementation (critical for TensorFlow 2.5.0)
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# Run worker (cloud version by default, local version for testing)
CMD ["python", "-u", "worker.py"]
