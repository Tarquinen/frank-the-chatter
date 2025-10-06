# Frank the Chatter - Discord Bot

A Discord bot that logs conversations to SQLite and responds intelligently with AI when mentioned.

## 🚀 Quick Setup

1. **Get API Keys:**
   - Discord Bot Token: https://discord.com/developers/applications
   - Google AI API Key: https://ai.google.dev/

2. **Setup Environment:**
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install -r config/requirements.txt
   ```

3. **Create `.env` file:**
   ```bash
   DISCORD_TOKEN=your_discord_bot_token_here
   GEMINI_API_KEY=your_google_gemini_api_key_here
   AI_MODEL=gemini-2.0-flash-001
   DATABASE_PATH=./data/conversations.db
   LOG_FILE_PATH=./data/logs/bot.log
   LOG_LEVEL=INFO
   ```

4. **Run:**
   ```bash
    ./scripts/run.sh
   ```

## ☁️ Deploy to Cloud VM

1. **Create VM** (Google Cloud, AWS, etc.)
2. **SSH and clone:**
   ```bash
   git clone <your-repo-url>
   cd frank-the-chatter
   ```
3. **Install Python:**
   ```bash
   sudo apt install python3 python3-pip python3-venv
   ```
4. **Setup and run:**
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install -r config/requirements.txt
   # Copy your .env file with API keys
    nohup ./scripts/run.sh > bot.log 2>&1 &
   ```

## 🤖 What Frank Does

- **Logs Everything:** All messages stored in SQLite database with timestamps
- **Smart Responses:** When @mentioned, responds with full conversation context using Gemini AI
- **Media Support:** Tracks Discord CDN URLs for all attachments  
- **Auto-Cleanup:** Maintains last 1000 messages per channel automatically
- **Production Ready:** Systemd service, monitoring, backups, error handling

## 📁 Project Structure

```
frank-the-chatter/
├── src/
│   ├── bot.py              # Main Discord bot
│   ├── database.py         # SQLite operations  
│   ├── message_storage.py  # Message handling
│   ├── ai_client.py        # Gemini AI integration
│   └── utils/
├── deploy/
│   ├── setup.sh           # Automated VM setup
│   ├── DEPLOYMENT.md      # Deployment guide
│   ├── monitor.sh         # Health monitoring  
│   ├── backup.sh          # Database backups
│   └── systemd/           # Service config
├── config/
│   ├── requirements.txt   # Python dependencies
│   ├── .env              # Development config
│   └── .env.production   # Production template
└── data/                 # SQLite database & logs
```

## 🛠 Management Commands

**Local Development:**
```bash
./scripts/run.sh              # Start bot locally
python test_ai.py     # Test AI integration
./scripts/db_query.py    # Query database
```

**Production (on Google Cloud VM):**
```bash
sudo systemctl start frank-bot     # Start service
sudo systemctl status frank-bot    # Check status  
sudo journalctl -u frank-bot -f    # View logs
./deploy/monitor.sh               # Health check
./deploy/backup.sh                # Create backup
```

## 🔧 Configuration

**Key Environment Variables:**
- `DISCORD_TOKEN` - Your Discord bot token
- `AI_API_KEY` - Google AI API key for Gemini
- `AI_MODEL` - AI model (default: gemini-2.0-flash-001)
- `DATABASE_PATH` - SQLite database location
- `LOG_LEVEL` - Logging verbosity (DEBUG/INFO)

**Performance Settings:**
- `MAX_MESSAGES_PER_CONVERSATION=1000` - Messages kept per channel
- `MAX_MESSAGE_CONTEXT_FOR_AI=100` - Messages sent to AI for context  
- `AI_MAX_TOKENS=2000` - Max response length (Discord limit friendly)

## 🎯 How Frank Responds

1. **User mentions @frank**: "Hey @frank, what do you think about this?"
2. **Frank retrieves context**: Last 100 messages from SQLite database
3. **AI generates response**: Using conversation history + personality prompt
4. **Frank replies**: Intelligent, contextual response posted to Discord

**Example interaction:**
```
User: "We've been talking about deployment strategies @frank"
Frank: "Based on our conversation, it sounds like you're weighing 
       container vs VM deployment. Given your requirements for 
       simplicity and cost, the e2-micro VM approach we discussed 
       earlier makes a lot of sense..."
```