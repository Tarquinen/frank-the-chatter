#!/bin/bash
# Run Frank the Chatter Discord Bot

cd "$(dirname "$0")"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please create .env with your Discord token:"
    echo "DISCORD_TOKEN=your_token_here"
    echo "GEMINI_API_KEY=your_gemini_key_here"
    exit 1
fi

# Run the bot
echo "Starting Frank the Chatter bot..."
echo "Press Ctrl+C to stop"
./venv/bin/python src/bot.py

