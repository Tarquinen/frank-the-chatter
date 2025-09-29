#!/bin/bash

# Frank the Chatter - Google Cloud VM Setup Script
# This script sets up the production environment on Ubuntu 22.04 LTS

set -e  # Exit on any error

echo "🚀 Starting Frank the Chatter deployment setup..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+ and required packages
echo "🐍 Installing Python and dependencies..."
sudo apt install -y python3 python3-pip python3-venv git sqlite3 curl

# Create application user
echo "👤 Creating frankbot user..."
if ! id "frankbot" &>/dev/null; then
    sudo useradd -m -s /bin/bash frankbot
    echo "frankbot ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/frankbot
fi

# Setup application directory
echo "📁 Setting up application directory..."
sudo mkdir -p /opt/frank-bot
sudo chown frankbot:frankbot /opt/frank-bot

# Clone or copy application code
echo "📥 Setting up application code..."
if [ ! -d "/opt/frank-bot/.git" ]; then
    # If running from local development, copy files
    if [ -d "$(pwd)/../src" ]; then
        echo "Copying local development files..."
        sudo -u frankbot cp -r $(pwd)/../* /opt/frank-bot/
    else
        echo "Please manually copy your application files to /opt/frank-bot/"
        echo "Or clone from your git repository"
    fi
fi

# Create data directories
echo "📂 Creating data directories..."
sudo -u frankbot mkdir -p /opt/frank-bot/data/logs

# Set up Python virtual environment
echo "🔧 Setting up Python virtual environment..."
cd /opt/frank-bot
sudo -u frankbot python3 -m venv venv
sudo -u frankbot ./venv/bin/pip install --upgrade pip
sudo -u frankbot ./venv/bin/pip install -r config/requirements.txt

# Create environment file template
echo "⚙️  Creating environment configuration..."
if [ ! -f "/opt/frank-bot/.env" ]; then
    sudo -u frankbot tee /opt/frank-bot/.env > /dev/null <<EOF
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token_here
BOT_USER_ID=your_bot_user_id_here

# AI API Configuration (Google Gemini)
GEMINI_API_KEY=your_google_gemini_api_key_here
AI_MODEL=gemini-2.5-flash
AI_MAX_TOKENS=2000

# Storage Configuration
DATABASE_PATH=./data/conversations.db
LOG_FILE_PATH=./data/logs/bot.log

# Performance Settings
MAX_ACTIVE_CONVERSATIONS=100
MAX_MESSAGES_PER_CONVERSATION=1000
MAX_MESSAGE_CONTEXT_FOR_AI=100

# Logging
LOG_LEVEL=INFO
DEBUG_MODE=false
EOF
    echo "⚠️  Please edit /opt/frank-bot/.env with your actual API keys"
fi

# Install systemd service
echo "🔧 Installing systemd service..."
sudo cp deploy/systemd/frank-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable frank-bot

# Set up firewall (optional but recommended)
echo "🔥 Configuring firewall..."
sudo ufw allow ssh
sudo ufw --force enable

# Initialize database
echo "🗄️  Initializing database..."
cd /opt/frank-bot
sudo -u frankbot ./venv/bin/python -c "
import sys
sys.path.append('src')
from database import MessageDatabase
db = MessageDatabase()
print('Database initialized successfully')
"

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit /opt/frank-bot/.env with your API keys"
echo "2. Test the bot: sudo -u frankbot /opt/frank-bot/venv/bin/python /opt/frank-bot/src/bot.py"
echo "3. Start the service: sudo systemctl start frank-bot"
echo "4. Check status: sudo systemctl status frank-bot"
echo "5. View logs: sudo journalctl -u frank-bot -f"
echo ""
echo "🎉 Frank the Chatter is ready for deployment!"