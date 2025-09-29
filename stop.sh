#!/bin/bash
# Stop Frank the Chatter Discord Bot

echo "Stopping Frank the Chatter..."

# Kill the bot process
pkill -f "src/bot.py"

# Wait a moment and check if it's really dead
sleep 2

if pgrep -f "src/bot.py" > /dev/null; then
    echo "Process still running, force killing..."
    pkill -9 -f "src/bot.py"
    sleep 1
fi

if pgrep -f "src/bot.py" > /dev/null; then
    echo "❌ Failed to stop Frank"
    exit 1
else
    echo "✅ Frank stopped successfully"
fi