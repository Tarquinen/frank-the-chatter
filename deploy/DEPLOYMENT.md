# Google Cloud VM Deployment Guide

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **Discord Bot Token** from Discord Developer Portal
3. **Google AI API Key** from Google AI Studio

## Step 1: Create Google Cloud VM

### Using Google Cloud Console:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **Compute Engine > VM instances**
3. Click **Create Instance**
4. Configure:
   - **Name**: `frank-bot-vm`
   - **Region**: `us-central1` (free tier eligible)
   - **Zone**: `us-central1-a`
   - **Machine type**: `e2-micro` (1 vCPU, 1GB memory)
   - **Boot disk**: Ubuntu 22.04 LTS, 30GB Standard persistent disk
   - **Firewall**: Allow HTTPS traffic
   - **Advanced options > Management > Startup script**: Leave empty for now

### Using gcloud CLI:

```bash
gcloud compute instances create frank-bot-vm \
    --zone=us-central1-a \
    --machine-type=e2-micro \
    --network-interface=network-tier=PREMIUM,subnet=default \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --service-account=your-service-account@your-project.iam.gserviceaccount.com \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --tags=https-server \
    --create-disk=auto-delete=yes,boot=yes,device-name=frank-bot-vm,image=projects/ubuntu-os-cloud/global/images/ubuntu-2204-jammy-v20231030,mode=rw,size=30,type=projects/your-project/zones/us-central1-a/diskTypes/pd-standard \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --labels=environment=production,app=frank-bot \
    --reservation-affinity=any
```

## Step 2: Connect to VM

```bash
# SSH into the VM
gcloud compute ssh frank-bot-vm --zone=us-central1-a

# Or use the console SSH button in Google Cloud Console
```

## Step 3: Deploy the Bot

### Method 1: Upload files directly

1. **Upload your code to the VM:**
   ```bash
   # From your local machine, upload the project
   gcloud compute scp --recurse /path/to/frank-the-chatter frank-bot-vm:~ --zone=us-central1-a
   ```

2. **Run the setup script:**
   ```bash
   # On the VM
   cd frank-the-chatter
   chmod +x deploy/setup.sh
   sudo ./deploy/setup.sh
   ```

### Method 2: Clone from Git (if you've pushed to a repository)

1. **Clone the repository on the VM:**
   ```bash
   git clone https://github.com/yourusername/frank-the-chatter.git
   cd frank-the-chatter
   chmod +x deploy/setup.sh
   sudo ./deploy/setup.sh
   ```

## Step 4: Configure Environment

1. **Edit the environment file:**
   ```bash
   sudo -u frankbot nano /opt/frank-bot/config/.env
   ```

2. **Set your API keys:**
   ```env
   DISCORD_TOKEN=your_actual_discord_bot_token
   BOT_USER_ID=your_bot_user_id
   AI_API_KEY=your_google_ai_api_key
   ```

## Step 5: Start and Test

1. **Test the bot manually:**
   ```bash
   sudo -u frankbot /opt/frank-bot/venv/bin/python /opt/frank-bot/src/bot.py
   ```
   Press Ctrl+C to stop after testing.

2. **Start the systemd service:**
   ```bash
   sudo systemctl start frank-bot
   sudo systemctl status frank-bot
   ```

3. **View logs:**
   ```bash
   sudo journalctl -u frank-bot -f
   ```

## Step 6: Monitoring

### Check bot status:
```bash
sudo systemctl status frank-bot
```

### View real-time logs:
```bash
sudo journalctl -u frank-bot -f
```

### Check system resources:
```bash
htop
df -h
```

### Restart if needed:
```bash
sudo systemctl restart frank-bot
```

## Troubleshooting

### Common Issues:

1. **Import errors**: Make sure all dependencies are installed in the virtual environment
2. **Permission errors**: Ensure frankbot user owns all files in `/opt/frank-bot`
3. **API key errors**: Verify your Discord token and Google AI API key are correct
4. **Database errors**: Check that SQLite database is initialized properly

### Debug commands:
```bash
# Check service logs
sudo journalctl -u frank-bot --since "1 hour ago"

# Test database connection
sudo -u frankbot /opt/frank-bot/venv/bin/python -c "
import sys; sys.path.append('/opt/frank-bot/src')
from database import Database
db = Database()
print('Database OK')
"

# Test AI connection
sudo -u frankbot /opt/frank-bot/venv/bin/python /opt/frank-bot/test_ai.py
```

## Cost Management

- **Free Tier**: e2-micro instance is free for 744 hours/month
- **Monitor usage**: Check Google Cloud Console billing page
- **Auto-shutdown**: Consider setting up auto-shutdown during low usage periods

## Security Best Practices

1. **Firewall**: Only allow SSH and necessary ports
2. **Updates**: Keep system updated with `sudo apt update && sudo apt upgrade`
3. **Monitoring**: Set up uptime monitoring and alerts
4. **Backups**: Regular database backups to Google Cloud Storage

## Next Steps

Once deployed:
1. Invite your bot to Discord servers
2. Test @frank mentions to verify AI responses
3. Monitor logs for any errors
4. Set up automated backups (optional)