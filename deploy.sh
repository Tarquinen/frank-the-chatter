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

# Add convenient aliases to .bashrc (only if not already present)
echo "⚙️ Adding Frank aliases to .bashrc..."
if ! grep -q "Frank the Chatter aliases" ~/.bashrc; then
    cat >> ~/.bashrc << 'EOF'

# Frank the Chatter aliases
alias sv="source venv/bin/activate"
alias pydev="python3 -m venv venv && sv && pip install --upgrade pip"
alias frank-query="./venv/bin/python db_query.py"
alias frank-start="nohup ./run.sh > bot.log 2>&1 &"
alias frank-stop="./stop.sh"
alias frank-restart="frank-stop && sleep 2 && frank-start"
alias frank-logs="tail -f bot.log"
alias frank-status="ps aux | grep 'src/bot.py' | grep -v grep"
EOF
else
    echo "Frank aliases already exist in .bashrc, skipping..."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Create .env file with your API keys:"
echo "   DISCORD_TOKEN=your_token_here"
echo "   GEMINI_API_KEY=your_key_here"
echo ""
echo "2. Load Frank aliases:"
echo "   source ~/.bashrc     # Required to load new aliases"
echo ""
echo "3. Use Frank commands:"
echo "   frank-start          # Start bot in background"
echo "   frank-stop           # Stop bot"  
echo "   frank-restart        # Stop and start bot"
echo "   frank-status         # Check if running"
echo "   frank-logs           # View logs"
echo "   frank-query stats    # Query database"
echo ""
echo "4. Or run manually:"
echo "   ./run.sh             # Run in foreground"