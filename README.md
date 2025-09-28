# Frank the Chatter - Discord Bot

A Discord bot that logs conversations to SQLite and responds intelligently with AI when mentioned. **Ready for production deployment!**

## ✅ Current Status: Phase 4 Complete

**All phases implemented:**
- ✅ **Phase 1:** Discord bot framework with message logging  
- ✅ **Phase 2:** SQLite database storage with conversation management
- ✅ **Phase 3:** AI integration with Google Gemini 2.0 Flash
- ✅ **Phase 4:** Production deployment infrastructure

## 🚀 Quick Deploy to Google Cloud

**For production deployment:**
```bash
# Follow the comprehensive deployment guide
cat deploy/DEPLOYMENT.md
```

## 🧪 Local Development

1. **Get API Keys:**
   - Discord Bot Token: https://discord.com/developers/applications
   - Google AI API Key: https://ai.google.dev/

2. **Setup Environment:**
   ```bash
   cp config/.env.production config/.env
   # Edit config/.env with your actual API keys
   ```

3. **Install and Run:**
   ```bash
   pip install -r config/requirements.txt
   ./run.sh
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
./run.sh              # Start bot locally
python test_ai.py     # Test AI integration
python db_query.py    # Query database
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