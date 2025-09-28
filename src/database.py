import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

class MessageDatabase:
    def __init__(self, db_path: str = "data/conversations.db"):
        self.db_path = db_path
        self._ensure_data_dir()
        self._init_database()
    
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    discord_message_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    content TEXT,
                    timestamp DATETIME NOT NULL,
                    has_attachments BOOLEAN DEFAULT FALSE,
                    media_files TEXT,  -- JSON array of file info
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS media_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    file_path TEXT,
                    discord_url TEXT NOT NULL,
                    file_type TEXT,
                    file_size INTEGER,
                    downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages(id)
                )
            ''')
            
            # Create indexes for fast queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_channel_timestamp ON messages(channel_id, timestamp DESC)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_discord_message_id ON messages(discord_message_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_media_message ON media_files(message_id)')
            
            conn.commit()
    
    def store_message(self, channel_id: str, discord_message_id: str, user_id: str, 
                     username: str, content: str, timestamp: datetime, 
                     attachments: List[Dict] = None) -> int:
        """
        Store a Discord message in the database
        
        Args:
            channel_id: Discord channel ID
            discord_message_id: Discord message ID
            user_id: Discord user ID
            username: Display name of user
            content: Message text content
            timestamp: When message was sent
            attachments: List of attachment info dicts
        
        Returns:
            Message ID from database
        """
        has_attachments = bool(attachments)
        media_files_json = json.dumps(attachments) if attachments else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO messages 
                (channel_id, discord_message_id, user_id, username, content, 
                 timestamp, has_attachments, media_files)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (channel_id, discord_message_id, user_id, username, content,
                  timestamp, has_attachments, media_files_json))
            
            message_id = cursor.lastrowid
            
            # Store individual media file records
            if attachments:
                for attachment in attachments:
                    conn.execute('''
                        INSERT INTO media_files 
                        (message_id, filename, discord_url, file_type, file_size)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (message_id, attachment['filename'], attachment['url'],
                          attachment.get('content_type'), attachment.get('size')))
            
            conn.commit()
            return message_id
    
    def get_recent_messages(self, channel_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent messages from a channel for AI context
        
        Args:
            channel_id: Discord channel ID
            limit: Number of recent messages to retrieve
            
        Returns:
            List of message dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT username, content, timestamp, has_attachments, media_files
                FROM messages 
                WHERE channel_id = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (channel_id, limit))
            
            messages = []
            for row in cursor.fetchall():
                message = {
                    'username': row['username'],
                    'content': row['content'],
                    'timestamp': row['timestamp'],
                    'has_attachments': bool(row['has_attachments']),
                    'media_files': json.loads(row['media_files']) if row['media_files'] else []
                }
                messages.append(message)
            
            # Return in chronological order (oldest first)
            return list(reversed(messages))
    
    def cleanup_old_messages(self, channel_id: str, keep_last: int = 1000):
        """
        Remove old messages from a channel, keeping only the most recent ones
        
        Args:
            channel_id: Discord channel ID
            keep_last: Number of recent messages to keep
        """
        with sqlite3.connect(self.db_path) as conn:
            # Find messages to delete (older than the last N messages)
            cursor = conn.execute('''
                SELECT id FROM messages 
                WHERE channel_id = ?
                ORDER BY timestamp DESC
                LIMIT -1 OFFSET ?
            ''', (channel_id, keep_last))
            
            old_message_ids = [row[0] for row in cursor.fetchall()]
            
            if old_message_ids:
                # Delete associated media files first
                placeholders = ','.join('?' * len(old_message_ids))
                conn.execute(f'''
                    DELETE FROM media_files 
                    WHERE message_id IN ({placeholders})
                ''', old_message_ids)
                
                # Delete old messages
                conn.execute(f'''
                    DELETE FROM messages 
                    WHERE id IN ({placeholders})
                ''', old_message_ids)
                
                conn.commit()
                print(f"Cleaned up {len(old_message_ids)} old messages from channel {channel_id}")
    
    def get_message_count(self, channel_id: str) -> int:
        """Get total number of messages for a channel"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT COUNT(*) FROM messages WHERE channel_id = ?', 
                (channel_id,)
            )
            return cursor.fetchone()[0]
    
    def get_channels_with_messages(self) -> List[Dict[str, Any]]:
        """Get list of all channels with message counts"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT channel_id, COUNT(*) as message_count, 
                       MAX(timestamp) as last_activity
                FROM messages 
                GROUP BY channel_id
                ORDER BY last_activity DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_media_file_path(self, message_id: int, filename: str, local_path: str):
        """Update the local file path for a downloaded media file"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE media_files 
                SET file_path = ?
                WHERE message_id = ? AND filename = ?
            ''', (local_path, message_id, filename))
            conn.commit()