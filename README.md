# Frank the Chatter - Discord Bot

A Discord bot that logs conversations and responds with AI when mentioned.

## Quick Start

1. **Get a Discord Bot Token:**
   - Go to https://discord.com/developers/applications
   - Create a new application and bot
   - Copy the bot token

2. **Setup Environment:**
   ```bash
   # Make sure .env has your tokens:
   DISCORD_TOKEN=your_bot_token_here
   GEMINI_API_KEY=your_gemini_key_here
   ```

3. **Run the Bot:**
   ```bash
   ./run.sh
   ```

## What It Does (Phase 1)

- ✅ Connects to Discord with proper authentication
- ✅ Logs all messages with timestamps 
- ✅ Stores last 1000 messages per channel in memory
- ✅ Responds when @mentioned with context info
- ✅ Comprehensive logging to console and files

## Commands

- **Start bot:** `./run.sh`
- **Stop bot:** Press `Ctrl+C`

## Files Structure

```
src/bot.py              # Main bot code
src/utils/config.py     # Configuration management
src/utils/logger.py     # Logging setup
config/requirements.txt # Python dependencies
config/.env            # Environment variables
data/logs/            # Log files (created automatically)
```

## Next Steps

- **Phase 2:** SQLite database storage
- **Phase 3:** AI integration with Gemini
- **Phase 4:** Media handling  
- **Phase 5:** Production deployment

## Troubleshooting

**Bot won't connect:**
- Check your Discord token in `.env`
- Make sure the bot has proper permissions in your server

**Permission errors:**
- Run `chmod +x run.sh` to make the script executable