# DrumScore Backend - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.8
- FFmpeg installed
- 10 GB free disk space

### Installation

**Option 1: Automated Setup (Recommended)**
```powershell
# Run the setup script
python setup.py
```

**Option 2: Manual Setup**
```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install Demucs
cd ..\demucs
pip install -e .

# Install Omnizart
cd ..\omnizart
pip install -e .

# Download model checkpoints
cd ..\backend
python -c "from omnizart.cli.cli import download_checkpoints; download_checkpoints()"

# Create directories
mkdir uploads, temp, outputs, models, logs

# Configure environment
cp .env.example .env
```

### Start Server

```powershell
cd backend
python main.py
```

Server starts at: **http://localhost:8000**

### Test It

1. **Visit Interactive Docs**: http://localhost:8000/docs

2. **Upload a test file**:
```powershell
curl -X POST "http://localhost:8000/api/v1/transcribe" `
  -F "audio_file=@your_song.mp3"
```

3. **Check status** (replace JOB_ID):
```powershell
curl "http://localhost:8000/api/v1/status/JOB_ID"
```

4. **Download results**:
```powershell
curl -O "http://localhost:8000/api/v1/download/JOB_ID/pdf"
```

### Docker Quick Start

```powershell
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📖 What Next?

- **API Documentation**: See [API.md](API.md)
- **Deployment Guide**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Full README**: See [README.md](README.md)

## 🔧 Common Issues

### "CUDA not available"
→ Set `DEMUCS_DEVICE=cpu` and `OMNIZART_DEVICE=cpu` in `.env`

### "Models not loading"
→ Run: `omnizart download-checkpoints` in backend directory

### "Port 8000 in use"
→ Change `PORT=8001` in `.env`

### "Out of memory"
→ Reduce `MAX_CONCURRENT_JOBS=1` in `.env`

## 📞 Support

- Check logs: `backend/logs/drumscore.log`
- Test API: `python test_api.py`
- Health check: http://localhost:8000/api/v1/health

---

🎵 Happy transcribing!
