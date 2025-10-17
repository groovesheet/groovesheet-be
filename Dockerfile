FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy demucs and omnizart repositories
COPY demucs /app/demucs
COPY omnizart /app/omnizart

# Copy backend application
COPY backend /app/backend

# Set working directory to backend
WORKDIR /app/backend

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install demucs
RUN cd /app/demucs && pip install -e .

# Install omnizart
RUN cd /app/omnizart && pip install -e .

# Download model checkpoints
RUN python -c "import omnizart; omnizart.download_checkpoints()" || echo "Checkpoints will be downloaded on first use"

# Create necessary directories
RUN mkdir -p /app/backend/uploads \
    /app/backend/temp \
    /app/backend/outputs \
    /app/backend/models \
    /app/backend/logs

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend:/app/demucs:/app/omnizart:$PYTHONPATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5m --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
