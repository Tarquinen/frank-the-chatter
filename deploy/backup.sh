#!/bin/bash

# Frank Bot Backup Script
# Creates backups of the bot's database and configuration

BACKUP_DIR="/opt/frank-bot/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BOT_DIR="/opt/frank-bot"

echo "🗄️  Frank Bot Backup - $TIMESTAMP"
echo "=================================="

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
echo "📦 Backing up database..."
if [ -f "$BOT_DIR/data/conversations.db" ]; then
    cp "$BOT_DIR/data/conversations.db" "$BACKUP_DIR/conversations_$TIMESTAMP.db"
    echo "✅ Database backed up to conversations_$TIMESTAMP.db"
else
    echo "⚠️  Database not found"
fi

# Backup configuration
echo "⚙️  Backing up configuration..."
if [ -f "$BOT_DIR/config/.env" ]; then
    # Remove sensitive data from backup
    grep -v "TOKEN\|API_KEY" "$BOT_DIR/config/.env" > "$BACKUP_DIR/config_$TIMESTAMP.env"
    echo "✅ Configuration backed up (without secrets)"
else
    echo "⚠️  Configuration not found"
fi

# Backup logs (last 1000 lines)
echo "📋 Backing up recent logs..."
journalctl -u frank-bot --lines=1000 > "$BACKUP_DIR/logs_$TIMESTAMP.txt"
echo "✅ Logs backed up"

# Cleanup old backups (keep last 10)
echo "🧹 Cleaning up old backups..."
cd "$BACKUP_DIR"
ls -t conversations_*.db | tail -n +11 | xargs -r rm
ls -t config_*.env | tail -n +11 | xargs -r rm  
ls -t logs_*.txt | tail -n +11 | xargs -r rm
echo "✅ Old backups cleaned up"

# Show backup summary
echo ""
echo "📊 Backup Summary:"
echo "   Location: $BACKUP_DIR"
echo "   Database: $(ls -la $BACKUP_DIR/conversations_$TIMESTAMP.db 2>/dev/null | awk '{print $5}') bytes"
echo "   Config: $(ls -la $BACKUP_DIR/config_$TIMESTAMP.env 2>/dev/null | awk '{print $5}') bytes"
echo "   Logs: $(ls -la $BACKUP_DIR/logs_$TIMESTAMP.txt 2>/dev/null | awk '{print $5}') bytes"

echo ""
echo "✅ Backup completed successfully!"

# Optional: Upload to Google Cloud Storage (uncomment if needed)
# echo "☁️  Uploading to Google Cloud Storage..."
# gsutil cp "$BACKUP_DIR/conversations_$TIMESTAMP.db" gs://your-backup-bucket/
# echo "✅ Uploaded to cloud storage"