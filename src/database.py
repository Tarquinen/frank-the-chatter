import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from utils.constants import (
    MAX_DATABASE_SIZE_GB,
    MAX_MESSAGES_PER_CHANNEL,
    DEFAULT_RECENT_MESSAGES,
    BYTES_PER_MB,
    MB_PER_GB,
    CLEANUP_DAYS_PRIMARY,
    CLEANUP_DAYS_SECONDARY,
    CLEANUP_CHANNEL_KEEP_LAST,
)


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
            conn.execute("""
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
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY,
                    channel_id TEXT UNIQUE,
                    channel_name TEXT,
                    last_activity DATETIME,
                    message_count INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for fast queries
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_channel_timestamp ON messages(channel_id, timestamp DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_discord_message_id ON messages(discord_message_id)"
            )

            conn.commit()

    def store_message(
        self,
        channel_id: str,
        discord_message_id: str,
        user_id: str,
        username: str,
        content: str,
        timestamp: datetime,
        attachments: Optional[List[Dict]] = None,
    ) -> int:
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
            cursor = conn.execute(
                """
                INSERT INTO messages 
                (channel_id, discord_message_id, user_id, username, content, 
                 timestamp, has_attachments, media_files)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    channel_id,
                    discord_message_id,
                    user_id,
                    username,
                    content,
                    timestamp,
                    has_attachments,
                    media_files_json,
                ),
            )

            message_id = cursor.lastrowid
            if message_id is None:
                raise ValueError("Failed to store message")

            conn.execute(
                """
                INSERT INTO conversations (channel_id, last_activity, message_count)
                VALUES (?, ?, 1)
                ON CONFLICT(channel_id) DO UPDATE SET
                    last_activity = ?,
                    message_count = (SELECT COUNT(*) FROM messages WHERE channel_id = ?)
                """,
                (channel_id, timestamp, timestamp, channel_id),
            )

            conn.commit()
            return message_id

    def get_recent_messages(
        self, channel_id: str, limit: int = DEFAULT_RECENT_MESSAGES
    ) -> List[Dict[str, Any]]:
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
            cursor = conn.execute(
                """
                SELECT username, content, timestamp, has_attachments, media_files
                FROM messages 
                WHERE channel_id = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """,
                (channel_id, limit),
            )

            messages = []
            for row in cursor.fetchall():
                message = {
                    "username": row["username"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                    "has_attachments": bool(row["has_attachments"]),
                    "media_files": json.loads(row["media_files"])
                    if row["media_files"]
                    else [],
                }
                messages.append(message)

            # Return in chronological order (oldest first)
            return list(reversed(messages))

    def delete_all_channel_messages(self, channel_id: str) -> int:
        """
        Delete ALL messages from a channel and remove the conversation record

        Args:
            channel_id: Discord channel ID

        Returns:
            Number of messages deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE channel_id = ?", (channel_id,)
            )
            deleted_messages = cursor.rowcount

            conn.execute(
                "DELETE FROM conversations WHERE channel_id = ?", (channel_id,)
            )

            conn.commit()
            return deleted_messages

    def delete_recent_messages(self, channel_id: str, limit: int) -> int:
        """
        Delete the most recent N messages from a channel

        Args:
            channel_id: Discord channel ID
            limit: Number of recent messages to delete

        Returns:
            Number of messages deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id FROM messages 
                WHERE channel_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (channel_id, limit),
            )

            message_ids = [row[0] for row in cursor.fetchall()]

            if message_ids:
                placeholders = ",".join("?" * len(message_ids))
                conn.execute(
                    f"""
                    DELETE FROM messages 
                    WHERE id IN ({placeholders})
                """,
                    message_ids,
                )

                cursor = conn.execute(
                    """
                    UPDATE conversations 
                    SET message_count = (
                        SELECT COUNT(*) FROM messages WHERE channel_id = ?
                    ),
                    last_activity = (
                        SELECT MAX(timestamp) FROM messages WHERE channel_id = ?
                    )
                    WHERE channel_id = ?
                """,
                    (channel_id, channel_id, channel_id),
                )

                conn.commit()
                return len(message_ids)

            return 0

    def cleanup_old_messages(self, channel_id: str, keep_last: int = MAX_MESSAGES_PER_CHANNEL):
        with sqlite3.connect(self.db_path) as conn:
            # Find messages to delete (older than the last N messages)
            cursor = conn.execute(
                """
                SELECT id FROM messages 
                WHERE channel_id = ?
                ORDER BY timestamp DESC
                OFFSET ?
            """,
                (channel_id, keep_last),
            )

            old_message_ids = [row[0] for row in cursor.fetchall()]

            if old_message_ids:
                # Delete old messages (media URLs are stored as JSON in messages table)
                placeholders = ",".join("?" * len(old_message_ids))
                conn.execute(
                    f"""
                    DELETE FROM messages 
                    WHERE id IN ({placeholders})
                """,
                    old_message_ids,
                )

                conn.execute(
                    """
                    UPDATE conversations 
                    SET message_count = (
                        SELECT COUNT(*) FROM messages WHERE channel_id = ?
                    ),
                    last_activity = (
                        SELECT MAX(timestamp) FROM messages WHERE channel_id = ?
                    )
                    WHERE channel_id = ?
                """,
                    (channel_id, channel_id, channel_id),
                )

                conn.commit()
                print(
                    f"Cleaned up {len(old_message_ids)} old messages from channel {channel_id}"
                )

    def get_message_count(self, channel_id: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE channel_id = ?", (channel_id,)
            )
            return cursor.fetchone()[0]

    def get_channels_with_messages(self) -> List[Dict[str, Any]]:
        """Get list of all channels with message counts"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT channel_id, COUNT(*) as message_count, 
                       MAX(timestamp) as last_activity
                FROM messages 
                GROUP BY channel_id
                ORDER BY last_activity DESC
            """)

            return [dict(row) for row in cursor.fetchall()]

    def get_database_size_mb(self) -> float:
        """Get current database file size in MB"""
        try:
            size_bytes = os.path.getsize(self.db_path)
            return size_bytes / BYTES_PER_MB
        except FileNotFoundError:
            return 0.0

    def get_total_message_count(self) -> int:
        """Get total number of messages across all channels"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM messages")
            return cursor.fetchone()[0]

    def cleanup_old_messages_by_age(self, days_to_keep: int = 30):
        """
        Remove messages older than specified days across all channels

        Args:
            days_to_keep: Keep messages newer than this many days
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM messages 
                WHERE timestamp < ?
            """,
                (cutoff_date,),
            )

            deleted_count = cursor.rowcount

            if deleted_count > 0:
                conn.execute("""
                    UPDATE conversations
                    SET message_count = (
                        SELECT COUNT(*) FROM messages WHERE messages.channel_id = conversations.channel_id
                    ),
                    last_activity = (
                        SELECT MAX(timestamp) FROM messages WHERE messages.channel_id = conversations.channel_id
                    )
                    WHERE channel_id IN (
                        SELECT DISTINCT channel_id FROM messages
                    )
                """)

            conn.commit()

            if deleted_count > 0:
                print(
                    f"Cleaned up {deleted_count} messages older than {days_to_keep} days"
                )

            return deleted_count

    def get_messages_by_date_range(
        self, channel_id: str, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get messages within a specific date range

        Args:
            channel_id: Discord channel ID
            start_date: Start of date range (inclusive)
            end_date: End of date range (exclusive)

        Returns:
            List of message dictionaries in chronological order
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT username, content, timestamp, has_attachments, media_files
                FROM messages 
                WHERE channel_id = ? AND timestamp >= ? AND timestamp < ?
                ORDER BY timestamp ASC
            """,
                (channel_id, start_date, end_date),
            )

            messages = []
            for row in cursor.fetchall():
                message = {
                    "username": row["username"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                    "has_attachments": bool(row["has_attachments"]),
                    "media_files": json.loads(row["media_files"])
                    if row["media_files"]
                    else [],
                }
                messages.append(message)

            return messages

    def cleanup_if_database_too_large(self, max_size_gb: float = MAX_DATABASE_SIZE_GB):
        """
        Perform cleanup if database exceeds size limit

        Args:
            max_size_gb: Maximum database size in GB before cleanup
        """
        current_size_mb = self.get_database_size_mb()
        max_size_mb = max_size_gb * MB_PER_GB

        if current_size_mb > max_size_mb:
            print(
                f"Database size ({current_size_mb:.1f}MB) exceeds limit ({max_size_mb:.1f}MB)"
            )

            # First try cleaning old messages (older than CLEANUP_DAYS_PRIMARY days)
            deleted_by_age = self.cleanup_old_messages_by_age(CLEANUP_DAYS_PRIMARY)

            # If still too large, clean older messages (older than CLEANUP_DAYS_SECONDARY days)
            if self.get_database_size_mb() > max_size_mb:
                deleted_by_age += self.cleanup_old_messages_by_age(CLEANUP_DAYS_SECONDARY)

            # If still too large, limit per-channel messages
            if self.get_database_size_mb() > max_size_mb:
                channels = self.get_channels_with_messages()
                for channel in channels:
                    if channel["message_count"] > MAX_MESSAGES_PER_CHANNEL:
                        self.cleanup_old_messages(channel["channel_id"], CLEANUP_CHANNEL_KEEP_LAST)

            new_size_mb = self.get_database_size_mb()
            print(f"Database cleanup complete. Size: {new_size_mb:.1f}MB")
