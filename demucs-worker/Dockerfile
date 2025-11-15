# Demucs worker service Dockerfile
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
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from parent context
COPY demucs-worker/requirements.txt .

# Install Python packages
RUN pip install --upgrade pip 'setuptools<60' wheel
RUN pip install 'Cython>=0.29.24'
RUN pip install 'numpy==1.24.0'

# Install old compatible google-cloud packages  
RUN pip install --no-deps 'google-cloud-storage==1.42.3' 'google-cloud-pubsub==2.8.0'
RUN pip install 'google-api-core<2.0' 'google-auth<2.0' 'googleapis-common-protos<2.0'

# Install other requirements
RUN pip install --no-cache-dir --default-timeout=300 --upgrade-strategy only-if-needed -r requirements.txt

# Copy worker service files
COPY demucs-worker/worker.py .
COPY demucs-worker/services/ /app/services/

# Force unbuffered output for real-time logs
ENV PYTHONUNBUFFERED=1

EXPOSE 8081

# Run worker (cloud version by default, local version for testing)
CMD ["python", "-u", "worker.py"]


