# Frank the Chatter — Discord Bot

A lightweight Discord bot that logs messages to SQLite and replies with AI when mentioned. Designed for easy local use and one-command VM setup.

## Quick Start (Local)

Prereqs: Python 3.11+, Git

1) Create a virtualenv and install deps
```bash
python3 -m venv venv
./venv/bin/pip install -r config/requirements.txt
```

2) Create .env in the repo root
```bash
DISCORD_TOKEN=your_discord_user_token  # self token required for discord.py-self
GEMINI_API_KEY=your_google_gemini_api_key   # optional but recommended
```

3) Run the bot
```bash
./scripts/run.sh
```

## Get a Discord Token (Self Token for discord.py-self)

High-level approach
- Log into Discord in your browser.
- Open Developer Tools → Network tab.
- Perform an action that triggers an authenticated request (switch channel, send a message).
- Locate a request to the Discord API (e.g., `https://discord.com/api/v9/...`).
- Inspect the request headers and copy the `authorization` value — that is your self token.
- Put it in `.env` as `DISCORD_TOKEN=...`.

Security
- Treat your token like a password; never share or commit it.
- If it’s exposed, rotate the token by changing your Discord password.

Note
- If you want to avoid self tokens and be ToS-compliant, the alternative is migrating this app to the official bot API (I can help with refactoring if you choose that route).

## Deploy on a VM

Run the setup script from anywhere in the repo (it jumps to repo root automatically):
```bash
bash deploy/setup.sh
```

What the script does
- Updates system packages via apt.
- Installs Python, pip, venv, and git.
- Creates a Python virtualenv and upgrades pip.
- Installs project deps from `config/requirements.txt`.
- Upgrades to the latest dev `discord.py-self` from GitHub.
- Patches `discord.py-self` for `global_name` support using `./scripts/patch_discord_global_name.sh`.
- Creates data directories (`data/` and `data/logs/`).
- Initializes the SQLite database (imports `MessageDatabase`).
- Adds helpful aliases to your `~/.bashrc`:
  - `sv` — source venv
  - `pydev` — create venv and upgrade pip
  - `frank-query` — run DB query tool (`./venv/bin/python scripts/db_query.py`)
  - `frank-start` — run bot in background via `nohup ./scripts/run.sh > bot.log 2>&1 &`
  - `frank-stop` — stop the bot
  - `frank-restart` — stop then start
  - `frank-logs` — tail `bot.log`
  - `frank-status` — check if `src/bot.py` is running

After it finishes
```bash
# 1) Ensure your .env exists (see Variables below)
# 2) Load aliases
source ~/.bashrc
# 3) Start and check
frank-start
frank-status
frank-logs
# 4) Stop if needed
frank-stop
```

Manual run alternative
```bash
./scripts/run.sh     # foreground, prints logs
```

## Variables (.env)

Example .env (placeholders)
```env
DISCORD_TOKEN=your_discord_user_token
GEMINI_API_KEY=your_google_gemini_api_key
AI_MODEL=gemini-2.5-flash
BOT_USER_ID=123456789012345678
DAN_USER_ID=123456789012345678
```

Required
- `DISCORD_TOKEN` — Discord user token (self token for discord.py-self).

Recommended
- `GEMINI_API_KEY` — enables AI replies (without it, Frank logs messages and replies with a fallback string).

Optional (defaults shown)
- `AI_MODEL` — default `gemini-2.5-flash`
- `AI_MAX_TOKENS` — default `2000`
- `DATABASE_PATH` — default `./data/conversations.db`
- `LOG_FILE_PATH` — default `./data/logs/bot.log`
- `LOG_LEVEL` — default `INFO`

Note: `frank-start` writes process output to `./bot.log`; the bot also writes structured logs to `LOG_FILE_PATH`.

## Diagnostics

- `tools/diagnose_user_data.py` — Logs raw Discord gateway payloads and parsed message attributes to verify the presence of `global_name` and related fields.
- `tools/test_raw_data.py` — Minimal client that prints `author.global_name` when seen in `MESSAGE_CREATE` events.
- `tools/diagnose_gemini.py` — Tests Gemini API with recent DB context to debug empty responses and configuration issues.

Run diagnostics with your `.env` configured, e.g.:
```bash
./venv/bin/python tools/diagnose_user_data.py
```

## Project Layout
```
frank-the-chatter/
├── src/
│   ├── bot.py                # Discord bot
│   ├── database.py           # SQLite operations
│   ├── message_storage.py    # Message handling
│   ├── ai_client.py          # Gemini integration
│   └── utils/
├── scripts/
│   ├── run.sh                # Start bot locally
│   ├── stop.sh               # Stop bot helper
│   ├── db_query.py           # Query/inspect the DB
│   └── patch_discord_global_name.sh
├── deploy/
│   └── setup.sh              # One-command VM setup
├── prompts/                  # System prompts
├── config/
│   └── requirements.txt      # Python dependencies
├── tools/                    # Diagnostics tools
└── tests/                    # Test scripts (optional to run)
```

## Troubleshooting
- Aliases not found: `source ~/.bashrc` (after running the setup script).
- Bot says AI unavailable: set `GEMINI_API_KEY` in `.env` and restart.
- Logs: check `./bot.log` (process output) and `./data/logs/bot.log` (structured logs).
