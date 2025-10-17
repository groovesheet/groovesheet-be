# DrumScore Backend - Deployment Guide

## Table of Contents
- [Local Development](#local-development)
- [Cloud Deployment Options](#cloud-deployment-options)
- [AWS Deployment](#aws-deployment)
- [Google Cloud Deployment](#google-cloud-deployment)
- [Azure Deployment](#azure-deployment)
- [Production Checklist](#production-checklist)

---

## Local Development

### Quick Start

1. **Run the setup script**:
```powershell
python setup.py
```

2. **Configure environment**:
Edit `backend/.env` with your settings

3. **Start the server**:
```powershell
cd backend
python main.py
```

4. **Test the API**:
Visit `http://localhost:8000/docs`

---

## Cloud Deployment Options

### Comparison

| Provider | Instance Type | GPU | Monthly Cost* | Setup Time |
|----------|--------------|-----|---------------|------------|
| AWS EC2 | g4dn.xlarge | T4 | ~$400 | 30 min |
| GCP | n1-standard-4 + T4 | T4 | ~$350 | 30 min |
| Azure | NC6s_v3 | V100 | ~$900 | 30 min |
| DigitalOcean | GPU Droplet | - | ~$200 | 20 min |

*Approximate costs for 24/7 operation

### Recommended: AWS EC2 with GPU

Best balance of cost, performance, and ease of setup.

---

## AWS Deployment

### Prerequisites
- AWS Account
- AWS CLI installed and configured
- Basic knowledge of EC2 and security groups

### Step 1: Launch EC2 Instance

1. **Go to EC2 Console** → Launch Instance

2. **Choose AMI**:
   - Select: "Deep Learning AMI (Ubuntu 20.04)" or similar
   - Or use: Ubuntu Server 20.04 LTS

3. **Choose Instance Type**:
   - Recommended: `g4dn.xlarge` (1 GPU, 4 vCPUs, 16 GB RAM)
   - Budget option: `t3.xlarge` (CPU only, 4 vCPUs, 16 GB RAM)

4. **Configure Instance**:
   - Storage: 100 GB SSD
   - Security Group: Allow ports 22 (SSH), 8000 (API), 443 (HTTPS)

5. **Create/Select Key Pair** for SSH access

6. **Launch Instance**

### Step 2: Connect to Instance

```bash
ssh -i your-key.pem ubuntu@your-instance-ip
```

### Step 3: Install Docker

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# For GPU support, install nvidia-docker2
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Log out and back in for group changes
exit
```

### Step 4: Deploy Application

```bash
# Re-connect
ssh -i your-key.pem ubuntu@your-instance-ip

# Clone repository
git clone https://github.com/your-username/drumscore-be.git
cd drumscore-be

# Configure environment
cp backend/.env.example backend/.env
nano backend/.env  # Edit settings

# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Step 5: Configure Domain & SSL (Optional)

```bash
# Install Nginx
sudo apt-get install nginx certbot python3-certbot-nginx

# Configure Nginx
sudo nano /etc/nginx/sites-available/drumscore

# Add configuration:
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/drumscore /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

### Step 6: Set up Auto-restart

```bash
# Create systemd service
sudo nano /etc/systemd/system/drumscore.service
```

```ini
[Unit]
Description=DrumScore Backend
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/drumscore-be
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

```bash
# Enable service
sudo systemctl enable drumscore
sudo systemctl start drumscore
```

---

## Google Cloud Deployment

### Step 1: Create VM Instance

```bash
# Using gcloud CLI
gcloud compute instances create drumscore-vm \
    --zone=us-central1-a \
    --machine-type=n1-standard-4 \
    --accelerator=type=nvidia-tesla-t4,count=1 \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=100GB \
    --tags=http-server,https-server
```

### Step 2: Install NVIDIA Drivers

```bash
# SSH into instance
gcloud compute ssh drumscore-vm

# Install drivers
curl https://raw.githubusercontent.com/GoogleCloudPlatform/compute-gpu-installation/main/linux/install_gpu_driver.py --output install_gpu_driver.py
sudo python3 install_gpu_driver.py
```

### Step 3: Follow AWS Steps 3-6

Installation and configuration are similar to AWS.

---

## Azure Deployment

### Step 1: Create VM

```bash
# Using Azure CLI
az vm create \
    --resource-group drumscore-rg \
    --name drumscore-vm \
    --image UbuntuLTS \
    --size Standard_NC6s_v3 \
    --admin-username azureuser \
    --generate-ssh-keys
```

### Step 2: Open Ports

```bash
az vm open-port --port 8000 --resource-group drumscore-rg --name drumscore-vm
az vm open-port --port 443 --resource-group drumscore-rg --name drumscore-vm
```

### Step 3: Follow AWS Steps 3-6

---

## Production Checklist

### Security
- [ ] Enable HTTPS with SSL certificate
- [ ] Configure firewall rules
- [ ] Set up authentication/API keys
- [ ] Implement rate limiting
- [ ] Regular security updates
- [ ] Secure environment variables

### Monitoring
- [ ] Set up CloudWatch/Stackdriver logs
- [ ] Configure alerting for errors
- [ ] Monitor disk space
- [ ] Track API usage
- [ ] Set up uptime monitoring

### Performance
- [ ] Enable GPU if available
- [ ] Configure proper resource limits
- [ ] Set up caching if needed
- [ ] Optimize concurrent job limits
- [ ] Regular cleanup of old files

### Backup & Recovery
- [ ] Backup configuration files
- [ ] Document recovery procedures
- [ ] Test restore process
- [ ] Keep model checkpoints safe

### Scaling
- [ ] Consider load balancer for multiple instances
- [ ] Set up auto-scaling if needed
- [ ] Use S3/Cloud Storage for files
- [ ] Consider managed database for job queue

---

## Cost Optimization

### 1. Use Spot Instances (AWS)
Save up to 70% with spot instances:

```bash
# Launch spot instance
aws ec2 request-spot-instances \
    --spot-price "0.30" \
    --instance-count 1 \
    --type "one-time" \
    --launch-specification file://specification.json
```

### 2. Auto-shutdown During Idle

Create a cron job to stop instance during off-hours:

```bash
# Stop at night (11 PM)
0 23 * * * docker-compose down && sudo shutdown -h now

# Auto-start in morning (requires external trigger)
```

### 3. Use CPU-Only for Development

For testing, use CPU instances which are 5-10x cheaper.

---

## Troubleshooting

### GPU Not Detected

```bash
# Check NVIDIA driver
nvidia-smi

# If not found, reinstall drivers
sudo apt-get purge nvidia*
sudo apt-get install nvidia-driver-470
sudo reboot
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Increase Docker memory limit
# Edit docker-compose.yml:
services:
  drumscore-backend:
    deploy:
      resources:
        limits:
          memory: 16G
```

### Slow Processing

- Check GPU usage: `nvidia-smi`
- Reduce concurrent jobs in `.env`
- Ensure SSD storage is used
- Check network latency for downloads

---

## Support

For deployment issues:
1. Check logs: `docker-compose logs`
2. Verify health: `curl http://localhost:8000/api/v1/health`
3. Review system resources: `htop`, `nvidia-smi`
4. Check disk space: `df -h`

---

Built with ❤️ for production deployment
