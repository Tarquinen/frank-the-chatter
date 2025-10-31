# Frank the Chatter - Discord Bot

A Discord bot that logs conversations and replies with AI when mentioned.



test change

## What It Does

- Logs all messages to SQLite database
- Responds with AI when mentioned (@Frank)
- Stores conversation context for smart replies
- Supports images and attachments
- Runs on local machine or VM

## Quick Setup

### 1. Install Dependencies
```bash
python3 -m venv venv
./venv/bin/pip install -r config/requirements.txt
```

### 2. Create .env File
```bash
DISCORD_TOKEN=your_discord_user_token
GEMINI_API_KEY=your_google_gemini_api_key
```

### 3. Run Bot
```bash
./scripts/run.sh
```

## Commands

- `!commands` - List all commands
- `!summarize [count|today|yesterday]` - Summarize conversation
- `!bh` - Get helpful advice from Larry
- `!roast @user` - Roast someone based on message history
- `!personality [@user]` - Show personality traits
- `!lobotomize [count|all]` - Clear bot memory (Dan only)

## Get Discord Token

1. Open Discord in browser
2. Press F12 → Network tab
3. Send a message or switch channels
4. Find Discord API request
5. Copy `authorization` header value
6. Paste as `DISCORD_TOKEN` in .env

## VM Deployment

Run setup script on VM:
```bash
bash deploy/setup.sh
```

Then use aliases:
```bash
frank-start    # Start bot
frank-status   # Check status
frank-logs     # View logs
frank-stop     # Stop bot
```

## Configuration

Required:
- `DISCORD_TOKEN` - Discord user token

Optional:
- `GEMINI_API_KEY` - Google Gemini API key (for AI replies)
- `AI_MODEL` - AI model (default: gemini-2.5-flash)
- `DATABASE_PATH` - Database location (default: ./data/conversations.db)
- `LOG_LEVEL` - Logging level (default: INFO)

## Troubleshooting

- **Bot not responding**: Check `DISCORD_TOKEN` in .env
- **No AI replies**: Add `GEMINI_API_KEY` to .env
- **Logs**: Check `./bot.log` and `./data/logs/bot.log`
- **Aliases not found**: Run `source ~/.bashrc` after VM setup
