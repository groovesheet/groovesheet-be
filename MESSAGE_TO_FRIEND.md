# 📧 Message to Send Your Friend

Hey! I set up Docker for the DrumScore backend so you don't have to deal with all those dependency issues on your Mac. Here's what to do:

## Quick Setup (5 Minutes + 10 Min Build Time)

### 1. Install Docker Desktop for Mac
Download and install from here: https://www.docker.com/products/docker-desktop

Make sure Docker Desktop is running (you'll see a whale icon in your menu bar).

### 2. Get the Code
```bash
git clone https://github.com/EdwardZehuaZhang/drumscore-be.git
cd drumscore-be
```

### 3. Run the Setup Script
```bash
chmod +x start-docker.sh
./start-docker.sh
```

That's it! The script will:
- Check if Docker is installed
- Build the container (takes about 10 minutes the first time)
- Start the service
- Open the API docs in your browser

### 4. Test It
Once the script completes, open: http://localhost:8000/docs

Or test from terminal:
```bash
curl http://localhost:8000/api/health
```

You should see: `{"status":"healthy","model_exists":true}`

## What This Solves

Docker automatically handles:
- ✅ Python 3.8 environment
- ✅ All dependencies (Cython, NumPy, TensorFlow, PyTorch, etc.)
- ✅ Correct installation order
- ✅ System packages (FFmpeg, build tools)
- ✅ Everything that was failing with setup.py

## Useful Commands

```bash
# View logs
docker-compose logs -f

# Stop
docker-compose down

# Restart
docker-compose restart
```

## Your Files

Everything is saved on your Mac:
- Uploads: `backend/uploads/`
- Outputs: `backend/outputs/`
- Logs: `backend/logs/`

## Troubleshooting

**If Docker isn't running:**
→ Start Docker Desktop from your Applications folder

**If port 8000 is busy:**
→ Let me know and I'll tell you how to change it

**If it's slow on M1/M2/M3:**
→ Let me know, there's a quick fix

## Need More Help?

Check these files in the repo:
- `DOCKER_MACOS.md` - Quick guide for Mac
- `DOCKER_QUICKSTART.md` - Detailed instructions
- `DOCKER_SETUP.md` - Comprehensive documentation

Let me know if you hit any issues!

---

**TL;DR:**
1. Install Docker Desktop
2. Clone the repo
3. Run `chmod +x start-docker.sh && ./start-docker.sh`
4. Wait 10 minutes
5. Open http://localhost:8000/docs

🎉 No more dependency hell!
