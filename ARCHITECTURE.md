# Frank the Chatter - Discord Bot Architecture

## Project Overview
A Discord bot that automatically logs conversations and responds with AI when mentioned. Deployed on Google Cloud e2-micro VM with local storage.

## Core Requirements
- Track last 1000 messages across up to 100 conversations
- Store images, GIFs, and other media attachments
- Respond with AI when mentioned (e.g., "@frank what do you think?")
- Deploy to Google Cloud e2-micro VM (free tier with 30GB storage)

## Architecture Design

### High-Level Components
```
┌─────────────────────────────────────────┐
│              Discord Bot                │
├─────────────────────────────────────────┤
│  • WebSocket Connection Management      │
│  • Message Event Handling              │
│  • Mention Detection & AI Triggering   │
│  • Media Download & Storage            │
└─────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│           Message Storage               │
├─────────────────────────────────────────┤
│  • In-Memory: Active conversations     │
│  • SQLite DB: Persistent storage       │
│  • File System: Media attachments      │
└─────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│            AI Integration               │
├─────────────────────────────────────────┤
│  • Context Preparation (last 100 msgs) │
│  • API Call Management                 │
│  • Response Processing                 │
└─────────────────────────────────────────┘
```

### Data Flow
1. **Message Received** → Store directly in SQLite + download media
2. **Bot Mentioned** → Query last 100 messages from database → Send to AI → Reply
3. **Database Maintenance** → Periodic cleanup of old messages (keep last 1000 per channel)

## Project Structure

```
frank-the-chatter/
├── src/
│   ├── bot.py                    # Main bot entry point
│   ├── message_storage.py        # Direct database message storage
│   ├── ai_client.py             # AI API integration
│   ├── media_handler.py         # Media download and storage
│   ├── database.py              # SQLite database operations
│   └── utils/
│       ├── __init__.py
│       ├── config.py            # Configuration management
│       └── logger.py            # Logging setup
├── data/
│   ├── conversations.db         # SQLite database
│   ├── media/                   # Downloaded attachments
│   │   ├── images/
│   │   ├── videos/
│   │   └── other/
│   └── logs/
│       └── bot.log             # Application logs
├── config/
│   ├── .env                    # Environment variables
│   ├── requirements.txt        # Python dependencies
│   └── prompt.txt             # AI personality prompt
├── deploy/
│   ├── setup.sh               # VM setup script
│   ├── systemd/
│   │   └── frank-bot.service  # Systemd service file
│   └── nginx/                 # Optional: reverse proxy config
│       └── frank-bot.conf
├── tests/
│   ├── test_message_storage.py
│   ├── test_ai_client.py
│   └── test_media_handler.py
├── ARCHITECTURE.md            # This file
├── README.md                  # Setup and usage instructions
└── .gitignore                # Git ignore rules
```

## Technical Implementation Details

### 1. Message Storage Strategy

**Direct Database Storage**
All messages are written directly to SQLite database as they're received from Discord. No in-memory caching - we query the database for recent messages when needed.

**SQLite Database Schema**
```sql
-- Conversations table
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    channel_id TEXT UNIQUE,
    channel_name TEXT,
    last_activity DATETIME,
    message_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Messages table (primary storage)
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    channel_id TEXT,
    discord_message_id TEXT UNIQUE,
    user_id TEXT,
    username TEXT,
    content TEXT,
    timestamp DATETIME,
    has_attachments BOOLEAN DEFAULT FALSE,
    media_files TEXT, -- JSON array of file paths
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Media files table (URLs only)
CREATE TABLE media_files (
    id INTEGER PRIMARY KEY,
    message_id INTEGER,
    filename TEXT,
    discord_url TEXT NOT NULL,    -- Discord CDN URL (permanent)
    content_type TEXT,
    file_size INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id)
);
```

### 2. Message Management Logic

**Database-First Approach**
- All messages written directly to SQLite as received
- Query database for recent messages when bot is mentioned
- Automatic cleanup of old messages (keep last 1000 per channel)
- Index on channel_id and timestamp for fast queries

**Message Retrieval for AI**
```python
def get_recent_messages(channel_id, limit=100):
    """Get last N messages from database for AI context"""
    return db.execute("""
        SELECT username, content, timestamp, media_files 
        FROM messages 
        WHERE channel_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (channel_id, limit))
```

### 3. AI Integration Workflow

**Mention Detection**
- Monitor for bot mentions in messages
- Extract context request from message
- Prepare conversation context

**Context Preparation**
```python
def prepare_ai_context(channel_id, mention_message):
    # Get last 100 messages from database
    recent_messages = get_recent_messages(channel_id, limit=100)
    
    # Format for AI API
    context = format_messages_for_ai(recent_messages)
    
    # Add personality prompt
    system_prompt = load_personality_prompt()
    
    return {
        'system': system_prompt,
        'messages': context,
        'user_query': mention_message
    }
```

### 4. Media Handling

**Discord CDN URLs**
Discord provides reliable, permanent CDN URLs for all media:
- `message.attachments[].url` contains Discord CDN links
- URLs are persistent and don't require authentication
- Format: `https://cdn.discordapp.com/attachments/{channel_id}/{message_id}/{filename}`
- File metadata available: `.filename`, `.size`, `.content_type`

**Storage Strategy - URLs Only**
Store only the Discord CDN URLs, no local file downloads:
```python
# Store Discord URL directly - no downloading needed
for attachment in message.attachments:
    media_info = {
        'filename': attachment.filename,
        'url': attachment.url,
        'content_type': attachment.content_type,
        'size': attachment.size
    }
```

**Supported Media Types**
- Images: jpg, png, gif, webp
- Videos: mp4, webm, mov  
- Documents: pdf, txt, doc, docx
- Any file type Discord accepts

**Why URLs Only:**
- Discord CDN is reliable and persistent
- Saves 15-20GB of disk space 
- Faster processing (no download time)
- No file management/cleanup needed
- URLs work indefinitely without authentication

### 5. Google Cloud VM Deployment

**VM Specifications**
- Instance: e2-micro (1 vCPU, 1GB RAM)
- OS: Ubuntu 22.04 LTS
- Storage: 30GB standard persistent disk
- Region: us-central1 (free tier eligible)

**System Setup**
```bash
# Install Python 3.10+
sudo apt update
sudo apt install python3.10 python3.10-pip python3.10-venv

# Create application user
sudo useradd -m -s /bin/bash frankbot
sudo usermod -aG sudo frankbot

# Setup application directory
sudo mkdir -p /opt/frank-bot
sudo chown frankbot:frankbot /opt/frank-bot
```

**Service Configuration (Systemd)**
```ini
[Unit]
Description=Frank Discord Bot
After=network.target

[Service]
Type=simple
User=frankbot
WorkingDirectory=/opt/frank-bot
ExecStart=/opt/frank-bot/venv/bin/python src/bot.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/opt/frank-bot

[Install]
WantedBy=multi-user.target
```

### 6. Configuration Management

**Environment Variables (.env)**
```env
# Discord Configuration
DISCORD_TOKEN=your_bot_token_here
BOT_USER_ID=your_bot_user_id

# AI API Configuration
AI_API_KEY=your_openai_api_key
AI_API_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
AI_MAX_TOKENS=2000

# Storage Configuration
DATABASE_PATH=./data/conversations.db
MEDIA_STORAGE_PATH=./data/media
LOG_FILE_PATH=./data/logs/bot.log

# Performance Settings
MAX_ACTIVE_CONVERSATIONS=100
MAX_MESSAGES_PER_CONVERSATION=1000
MAX_MESSAGE_CONTEXT_FOR_AI=100
MAX_MEDIA_FILE_SIZE_MB=50

# Logging
LOG_LEVEL=INFO
DEBUG_MODE=false
```

## Implementation Phases

### Phase 1: Core Bot Framework
- [ ] Basic Discord bot connection
- [ ] Message event handling
- [ ] In-memory message storage
- [ ] Simple mention detection

### Phase 2: Storage System
- [ ] SQLite database setup
- [ ] Message archival system
- [ ] Conversation management
- [ ] Data persistence on restart

### Phase 3: AI Integration
- [ ] AI API client implementation
- [ ] Context preparation logic
- [ ] Response generation and posting
- [ ] Error handling and retries

### Phase 4: Media Handling
- [ ] Attachment detection and download
- [ ] File organization system
- [ ] Media metadata storage
- [ ] Cleanup and maintenance

### Phase 5: Production Deployment
- [ ] VM setup automation
- [ ] Service configuration
- [ ] Monitoring and logging
- [ ] Backup and recovery procedures

## Monitoring and Maintenance

**Health Checks**
- Discord connection status
- Database connectivity
- Disk space monitoring
- Memory usage tracking

**Logging Strategy**
- Application logs: INFO level for normal operations
- Error logs: Detailed error tracking with stack traces
- Performance logs: Response times, API call metrics
- Audit logs: Message processing, AI interactions

**Backup Strategy**
- Daily SQLite database backup to Google Cloud Storage
- Weekly full media backup
- Configuration backup on changes

## Security Considerations

**API Keys and Secrets**
- Store sensitive data in environment variables
- Use Google Secret Manager for production
- Rotate API keys regularly

**File System Security**
- Restrict file permissions (600 for configs, 755 for executables)
- Validate uploaded files for security threats
- Implement size limits and type restrictions

**Network Security**
- Configure UFW firewall (allow only SSH and HTTPS)
- Regular security updates via unattended-upgrades
- Monitor unusual network activity

## Cost Estimation

**Monthly Costs (USD)**
- e2-micro VM: $0 (free tier)
- Persistent disk (30GB): ~$1.20
- Network egress: ~$1-5 (depending on usage)
- AI API calls: Variable (estimate $10-50/month)

**Total estimated cost: $12-56/month**