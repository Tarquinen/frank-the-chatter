#!/bin/bash

# Simple deployment script for Frank the Chatter
# Run this on your VM after cloning the repo

set -e  # Exit on any error

echo "🤖 Setting up Frank the Chatter..."

# Update system packages
echo "📦 Updating system..."
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
echo "🐍 Installing Python..."
sudo apt install -y python3 python3-pip python3-venv git

# Create virtual environment
echo "🔧 Setting up Python environment..."
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r config/requirements.txt

# Create data directories
echo "📂 Creating data directories..."
mkdir -p data/logs

# Initialize database
echo "🗄️ Initializing database..."
./venv/bin/python -c "
import sys
sys.path.append('src')
from database import MessageDatabase
db = MessageDatabase()
print('✅ Database initialized')
"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Create .env file with your API keys:"
echo "   DISCORD_TOKEN=your_token_here"
echo "   GEMINI_API_KEY=your_key_here"
echo ""
echo "2. Run the bot:"
echo "   ./run.sh                    # Run in foreground"
echo "   nohup ./run.sh &            # Run in background"
echo ""
echo "3. View logs:"
echo "   tail -f bot.log             # If running with nohup"
echo "   tail -f data/logs/bot.log   # Bot's internal logs"