#!/usr/bin/env python3
"""Database query helper for Frank the Chatter bot"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import json

# Add src to path so we can import config
sys.path.append(str(Path(__file__).parent / "src"))

from utils.config import Config

def connect_db():
    """Connect to the bot database"""
    return sqlite3.connect(Config.DATABASE_PATH)

def show_schema():
    """Show database schema"""
    print("=== DATABASE SCHEMA ===\n")
    with connect_db() as conn:
        cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' ORDER BY name")
        for row in cursor:
            if row[0]:  # Skip empty rows
                print(row[0] + ";\n")

def show_stats():
    """Show database statistics"""
    print("=== DATABASE STATISTICS ===")
    with connect_db() as conn:
        # Count totals
        cursor = conn.execute("""
            SELECT 
                (SELECT COUNT(*) FROM messages) as total_messages,
                (SELECT COUNT(*) FROM conversations) as total_conversations,
                (SELECT COUNT(*) FROM messages WHERE has_attachments = 1) as messages_with_media
        """)
        totals = cursor.fetchone()
        print(f"Total Messages: {totals[0]}")
        print(f"Total Conversations: {totals[1]}")
        print(f"Messages with Media: {totals[2]}")
        
        # Show conversation breakdown
        print("\n=== CONVERSATIONS ===")
        cursor = conn.execute("""
            SELECT channel_id, channel_name, message_count, last_activity
            FROM conversations 
            ORDER BY last_activity DESC
        """)
        for row in cursor:
            channel_id, channel_name, msg_count, last_activity = row
            print(f"Channel {channel_id}: {msg_count} messages (last: {last_activity})")

def show_recent_messages(limit=10):
    """Show recent messages across all channels"""
    print(f"\n=== LAST {limit} MESSAGES ===")
    with connect_db() as conn:
        cursor = conn.execute("""
            SELECT channel_id, username, content, timestamp, has_attachments
            FROM messages 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        for row in cursor:
            channel_id, username, content, timestamp, has_attachments = row
            media_indicator = " [📎]" if has_attachments else ""
            content_preview = content[:80] + "..." if len(content) > 80 else content
            print(f"[{timestamp[:19]}] {username}: {content_preview}{media_indicator}")

def show_channel_messages(channel_id, limit=10):
    """Show messages from a specific channel"""
    print(f"\n=== MESSAGES FROM CHANNEL {channel_id} (last {limit}) ===")
    with connect_db() as conn:
        cursor = conn.execute("""
            SELECT username, content, timestamp, has_attachments, media_files
            FROM messages 
            WHERE channel_id = ?
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (channel_id, limit))
        
        for row in cursor:
            username, content, timestamp, has_attachments, media_files = row
            media_info = ""
            if has_attachments and media_files:
                try:
                    attachments = json.loads(media_files)
                    media_info = f" [+{len(attachments)} files]"
                except:
                    media_info = " [+attachments]"
            
            print(f"[{timestamp[:19]}] {username}: {content}{media_info}")

def clear_channel(channel_id, confirm=False):
    """Clear all messages from a specific channel"""
    with connect_db() as conn:
        # First, check if channel exists and get message count
        cursor = conn.execute("SELECT message_count, channel_name FROM conversations WHERE channel_id = ?", (channel_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"Channel {channel_id} not found in database")
            return
        
        message_count, channel_name = result
        channel_display = channel_name if channel_name else channel_id
        
        if message_count == 0:
            print(f"Channel '{channel_display}' already has no messages")
            return
        
        if not confirm:
            print(f"WARNING: This will delete {message_count} messages from channel '{channel_display}'")
            print(f"To confirm, run: python db_query.py clear {channel_id} --confirm")
            return
        
        try:
            # Delete messages from the channel
            cursor = conn.execute("DELETE FROM messages WHERE channel_id = ?", (channel_id,))
            deleted_count = cursor.rowcount
            
            # Update conversation record
            conn.execute("""
                UPDATE conversations 
                SET message_count = 0, last_activity = CURRENT_TIMESTAMP
                WHERE channel_id = ?
            """, (channel_id,))
            
            conn.commit()
            print(f"Successfully deleted {deleted_count} messages from channel '{channel_display}'")
            
        except Exception as e:
            print(f"Error clearing channel: {e}")
            conn.rollback()

def custom_query(query):
    """Execute a custom SQL query"""
    print(f"\n=== CUSTOM QUERY ===")
    print(f"Query: {query}\n")
    
    with connect_db() as conn:
        try:
            cursor = conn.execute(query)
            
            # Get column names
            columns = [description[0] for description in cursor.description] if cursor.description else []
            
            if columns:
                print(" | ".join(columns))
                print("-" * (len(" | ".join(columns))))
                
                for row in cursor:
                    print(" | ".join(str(cell) for cell in row))
            else:
                print("Query executed successfully (no results to display)")
                
        except Exception as e:
            print(f"Error executing query: {e}")

def main():
    """Main CLI interface"""
    if len(sys.argv) == 1:
        print("Frank the Chatter - Database Query Tool")
        print("\nUsage:")
        print("  python db_query.py schema          - Show database schema")
        print("  python db_query.py stats           - Show database statistics")
        print("  python db_query.py recent [N]      - Show N recent messages (default 10)")
        print("  python db_query.py channel <id> [N] - Show N messages from channel (default 10)")
        print("  python db_query.py clear <id>      - Clear all messages from channel (requires --confirm)")
        print("  python db_query.py query <SQL>     - Execute custom SQL query")
        print("\nExamples:")
        print("  python db_query.py recent 20")
        print("  python db_query.py channel 1421920063572934678")
        print("  python db_query.py clear 1421920063572934678 --confirm")
        print('  python db_query.py query "SELECT username, COUNT(*) FROM messages GROUP BY username"')
        return
    
    command = sys.argv[1].lower()
    
    if command == "schema":
        show_schema()
    elif command == "stats":
        show_stats()
    elif command == "recent":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        show_recent_messages(limit)
    elif command == "channel":
        if len(sys.argv) < 3:
            print("Error: Channel ID required")
            return
        channel_id = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        show_channel_messages(channel_id, limit)
    elif command == "clear":
        if len(sys.argv) < 3:
            print("Error: Channel ID required")
            return
        channel_id = sys.argv[2]
        confirm = "--confirm" in sys.argv
        clear_channel(channel_id, confirm)
    elif command == "query":
        if len(sys.argv) < 3:
            print("Error: SQL query required")
            return
        query = " ".join(sys.argv[2:])
        custom_query(query)
    else:
        print(f"Unknown command: {command}")
        print("Run without arguments to see usage help")

if __name__ == "__main__":
    main()