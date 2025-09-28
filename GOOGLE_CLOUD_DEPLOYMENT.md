# Google Cloud Free Tier Deployment Guide

Deploy Frank the Chatter Discord bot to Google Cloud's free tier e2-micro instance.

## Prerequisites

- Google Cloud account with $300 free trial credits (new users)
- GitHub repository with your bot code
- Discord bot token and Gemini API key

## Free Tier Specifications

- **Instance**: e2-micro (1 shared vCPU, 1 GB RAM)
- **Disk**: 30 GB standard persistent disk
- **Network**: 1 GB outbound data/month
- **Regions**: US only (us-west1, us-central1, us-east1)
- **Cost**: Free for first VM instance per month

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "New Project"
3. Name: `frank-bot-production`
4. Click "Create"
5. Enable billing (required for free tier)

## Step 2: Enable Required APIs

```bash
# Enable Compute Engine API
gcloud services enable compute.googleapis.com
```

Or via Console:
1. Go to APIs & Services > Library
2. Search and enable "Compute Engine API"

## Step 3: Create VM Instance

### Via Console (Recommended for First Time)

1. Go to Compute Engine > VM instances
2. Click "Create Instance"
3. Configure:
   - **Name**: `frank-bot-vm`
   - **Region**: `us-central1` (Iowa)
   - **Zone**: `us-central1-a`
   - **Machine type**: `e2-micro` (1 vCPU, 1 GB memory)
   - **Boot disk**: Ubuntu 22.04 LTS, 30 GB standard persistent disk
   - **Firewall**: Allow HTTP and HTTPS traffic (optional)
4. Click "Create"

### Via Command Line

```bash
# Set project
gcloud config set project frank-bot-production

# Create VM instance
gcloud compute instances create frank-bot-vm \
    --zone=us-central1-a \
    --machine-type=e2-micro \
    --network-interface=network-tier=PREMIUM,subnet=default \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --service-account=frank-bot-production@appspot.gserviceaccount.com \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --create-disk=auto-delete=yes,boot=yes,device-name=frank-bot-vm,image=projects/ubuntu-os-cloud/global/images/ubuntu-2204-jammy-v20240319,mode=rw,size=30,type=projects/frank-bot-production/zones/us-central1-a/diskTypes/pd-standard \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --reservation-affinity=any
```

## Step 4: Connect to VM

### Via Console
1. Go to Compute Engine > VM instances
2. Click "SSH" next to your instance

### Via Command Line
```bash
gcloud compute ssh frank-bot-vm --zone=us-central1-a
```

## Step 5: Deploy Frank Bot

Once connected to your VM:

### 1. Clone Repository
```bash
# Clone your repository (replace with your actual repo URL)
git clone https://github.com/yourusername/frank-the-chatter.git
cd frank-the-chatter
```

### 2. Run Setup Script
```bash
# Make setup script executable
chmod +x deploy/setup.sh

# Run deployment setup
./deploy/setup.sh
```

The setup script will:
- Install Python 3.10, pip, git, sqlite3
- Create `frankbot` system user
- Set up `/opt/frank-bot` directory
- Create Python virtual environment
- Install dependencies from `config/requirements.txt`
- Create systemd service
- Initialize SQLite database
- Configure firewall

### 3. Configure Environment
```bash
# Edit configuration file
sudo nano /opt/frank-bot/config/.env
```

Add your actual API keys:
```env
# Discord Configuration
DISCORD_TOKEN=your_actual_discord_bot_token
BOT_USER_ID=your_bot_user_id

# AI API Configuration (Google Gemini)
AI_API_KEY=your_actual_google_ai_api_key
AI_MODEL=gemini-2.0-flash-001
AI_MAX_TOKENS=2000

# Storage Configuration
DATABASE_PATH=./data/conversations.db
LOG_FILE_PATH=./data/logs/bot.log

# Performance Settings (Optimized for e2-micro)
MAX_ACTIVE_CONVERSATIONS=50
MAX_MESSAGES_PER_CONVERSATION=500
MAX_MESSAGE_CONTEXT_FOR_AI=50

# Logging
LOG_LEVEL=INFO
DEBUG_MODE=false
```

### 4. Test and Start Bot
```bash
# Test bot manually first
sudo -u frankbot /opt/frank-bot/venv/bin/python /opt/frank-bot/src/bot.py

# If test successful, start as service
sudo systemctl start frank-bot
sudo systemctl status frank-bot
```

## Step 6: Monitoring and Management

### Check Bot Status
```bash
# Run health check script
/opt/frank-bot/deploy/monitor.sh
```

### Common Commands
```bash
# View logs
sudo journalctl -u frank-bot -f

# Restart service
sudo systemctl restart frank-bot

# Stop service
sudo systemctl stop frank-bot

# Check service status
sudo systemctl status frank-bot
```

### Monitor Resource Usage
```bash
# Check memory usage
free -h

# Check disk space
df -h

# Monitor processes
htop
```

## Performance Optimization for e2-micro

### Resource Limits Set in systemd Service
- **Memory**: 800M max (out of 1GB total)
- **CPU**: 80% quota
- **Disk**: Read/write only to `/opt/frank-bot/data`

### Configuration Optimizations
- Reduced `MAX_ACTIVE_CONVERSATIONS` to 50
- Reduced `MAX_MESSAGE_CONTEXT_FOR_AI` to 50
- Set `LOG_LEVEL=INFO` (not DEBUG)

### Optional Performance Tweaks
```bash
# Reduce swappiness (use less swap)
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# Apply immediately
sudo sysctl vm.swappiness=10
```

## Cost Management

### Free Tier Limits
- **Compute**: 1 e2-micro instance free per month
- **Storage**: 30 GB standard persistent disk included
- **Network**: 1 GB outbound per month (inbound free)

### Monitor Usage
1. Go to Cloud Console > Billing
2. Check "Reports" for usage tracking
3. Set up billing alerts at $10, $50, $100

### Cost Optimization Tips
- Keep VM in US regions only
- Use standard persistent disk (not SSD)
- Monitor outbound network usage
- Consider stopping VM during maintenance

## Backup and Updates

### Database Backup Script
```bash
# Add to crontab for daily backups
echo "0 2 * * * /opt/frank-bot/deploy/backup.sh" | sudo crontab -u frankbot -
```

### Update Deployment
```bash
# SSH into VM
gcloud compute ssh frank-bot-vm --zone=us-central1-a

# Update code
cd /opt/frank-bot
sudo -u frankbot git pull origin main
sudo -u frankbot ./venv/bin/pip install -r config/requirements.txt
sudo systemctl restart frank-bot
```

## Security Considerations

### Firewall Configuration
```bash
# Check current firewall rules
sudo ufw status

# Only SSH should be open for Discord bot
sudo ufw allow ssh
sudo ufw enable
```

### User Permissions
- Bot runs as `frankbot` user (not root)
- Limited file system access via systemd
- No sudo privileges for frankbot user in production

### API Key Security
- Store keys in `/opt/frank-bot/config/.env` only
- File permissions: 600 (readable only by frankbot user)
- Never commit `.env` to version control

## Troubleshooting

### Bot Won't Start
```bash
# Check logs for errors
sudo journalctl -u frank-bot -n 50

# Test Python environment
sudo -u frankbot /opt/frank-bot/venv/bin/python -c "import discord; import google.genai; print('All imports successful')"
```

### Memory Issues
```bash
# Check memory usage
free -h
ps aux | grep python

# Restart if needed
sudo systemctl restart frank-bot
```

### Network Issues
```bash
# Test internet connectivity
ping google.com

# Check Discord connectivity
curl -I https://discord.com/api/v10/gateway
```

### Database Issues
```bash
# Check database file
ls -la /opt/frank-bot/data/conversations.db

# Test database connection
sudo -u frankbot /opt/frank-bot/venv/bin/python -c "
import sys; sys.path.append('/opt/frank-bot/src')
from database import MessageDatabase
db = MessageDatabase()
print('Database connection successful')
"
```

## Maintenance Schedule

### Daily (Automated)
- Database backup via cron job
- Log rotation
- Health monitoring

### Weekly
- Check VM resource usage
- Review bot logs for errors
- Monitor Google Cloud billing

### Monthly
- Update system packages: `sudo apt update && sudo apt upgrade`
- Review and clean old log files
- Check free tier usage limits

## Support and Resources

- **Google Cloud Documentation**: https://cloud.google.com/compute/docs
- **Free Tier Details**: https://cloud.google.com/free/docs/gcp-free-tier
- **Discord.py Documentation**: https://discordpy.readthedocs.io/
- **Gemini API Documentation**: https://ai.google.dev/docs

## Summary

This deployment leverages Google Cloud's free tier to run Frank the Chatter 24/7 at no cost for the first year (with $300 credits) and minimal cost afterward. The e2-micro instance provides sufficient resources for a Discord bot with proper configuration and monitoring.

Key benefits:
- ✅ True 24/7 uptime
- ✅ Professional systemd service management
- ✅ Automated monitoring and health checks
- ✅ Secure deployment with proper user permissions
- ✅ Scalable architecture for future growth
- ✅ Cost-effective with Google Cloud free tier