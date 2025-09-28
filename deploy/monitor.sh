#!/bin/bash

# Frank Bot Monitoring Script
# Run this script to check the health of your Discord bot

echo "🔍 Frank Bot Health Check"
echo "========================="

# Check if service is running
echo -n "Service Status: "
if systemctl is-active --quiet frank-bot; then
    echo "✅ Running"
else
    echo "❌ Not Running"
    echo "Attempting to start..."
    sudo systemctl start frank-bot
    sleep 3
    if systemctl is-active --quiet frank-bot; then
        echo "✅ Started successfully"
    else
        echo "❌ Failed to start"
        exit 1
    fi
fi

# Check recent logs for errors
echo -n "Recent Errors: "
error_count=$(journalctl -u frank-bot --since "1 hour ago" | grep -i error | wc -l)
if [ "$error_count" -eq 0 ]; then
    echo "✅ No errors in last hour"
else
    echo "⚠️  $error_count errors found in last hour"
    echo "Last 3 errors:"
    journalctl -u frank-bot --since "1 hour ago" | grep -i error | tail -3
fi

# Check database
echo -n "Database: "
if [ -f "/opt/frank-bot/data/conversations.db" ]; then
    db_size=$(du -h /opt/frank-bot/data/conversations.db | cut -f1)
    echo "✅ Accessible ($db_size)"
else
    echo "❌ Not found"
fi

# Check disk space
echo -n "Disk Space: "
disk_usage=$(df /opt/frank-bot | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$disk_usage" -lt 80 ]; then
    echo "✅ $disk_usage% used"
else
    echo "⚠️  $disk_usage% used (getting full)"
fi

# Check memory usage
echo -n "Memory Usage: "
memory_usage=$(free | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')
echo "📊 $memory_usage"

# Check last bot activity
echo -n "Last Activity: "
last_log=$(journalctl -u frank-bot --since "1 day ago" | tail -1)
if [ -n "$last_log" ]; then
    echo "✅ Recent activity detected"
else
    echo "⚠️  No recent activity"
fi

echo ""
echo "📊 Quick Stats:"
echo "   Uptime: $(systemctl show frank-bot --property=ActiveEnterTimestamp --value | xargs -I {} date -d {} '+%Y-%m-%d %H:%M:%S')"
echo "   PID: $(systemctl show frank-bot --property=MainPID --value)"

# Show last 5 log lines
echo ""
echo "📋 Recent Logs:"
journalctl -u frank-bot --lines=5 --no-pager

echo ""
echo "🔧 Management Commands:"
echo "   Restart: sudo systemctl restart frank-bot"
echo "   Stop:    sudo systemctl stop frank-bot"
echo "   Logs:    sudo journalctl -u frank-bot -f"
echo "   Status:  sudo systemctl status frank-bot"