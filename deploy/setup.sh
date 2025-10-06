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

# Upgrade to latest discord.py-self dev version (required for search() method)
echo "🔧 Upgrading discord.py-self to latest dev version..."
./venv/bin/pip install --upgrade git+https://github.com/dolfies/discord.py-self.git

# Patch discord.py-self to support global_name
echo "🔧 Patching discord.py-self for display name support..."
./scripts/patch_discord_global_name.sh

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

# Add/update convenient aliases in .bashrc
echo "⚙️ Adding/updating Frank aliases in .bashrc..."

# Remove old Frank aliases if they exist
sed -i '/# Frank the Chatter aliases/,/^$/d' ~/.bashrc

# Add current Frank aliases
cat >> ~/.bashrc << 'EOF'

# Frank the Chatter aliases
alias sv="source venv/bin/activate"
alias pydev="python3 -m venv venv && sv && pip install --upgrade pip"
alias frank-query="./venv/bin/python scripts/db_query.py"
alias frank-start="nohup ./scripts/run.sh > bot.log 2>&1 &"
alias frank-stop="./scripts/stop.sh"
alias frank-restart="frank-stop && sleep 2 && frank-start"
alias frank-logs="tail -f bot.log"
alias frank-status="ps aux | grep 'src/bot.py' | grep -v grep"
EOF

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
echo "   ./scripts/run.sh     # Run in foreground"