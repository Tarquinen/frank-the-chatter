from datetime import datetime
from typing import Any

import discord

from database import MessageDatabase
from utils.config import Config
from utils.constants import (
    DB_SIZE_CHECK_INTERVAL,
    MAX_DATABASE_SIZE_GB,
    MAX_MESSAGES_PER_CHANNEL,
    MB_PER_GB,
    MESSAGES_CLEANUP_MARGIN,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MessageStorage:
    """
    Direct database storage for Discord messages
    Handles message archival and conversation management
    """

    def __init__(self, db_path: str | None = None):
        # Use config path by default
        self.db_path = db_path or Config.DATABASE_PATH
        self.db = MessageDatabase(self.db_path)
        self.last_size_check = datetime.now()
        self.size_check_interval = DB_SIZE_CHECK_INTERVAL
        logger.info(f"MessageStorage initialized with database: {self.db_path}")

    def store_message(self, message: discord.Message) -> int:
        channel_id = str(message.channel.id)
        discord_message_id = str(message.id)
        user_id = str(message.author.id)
        username = message.author.display_name
        content = message.content or ""
        timestamp = message.created_at

        attachments = []
        if message.attachments:
            for attachment in message.attachments:
                attachments.append(
                    {
                        "filename": attachment.filename,
                        "url": attachment.url,
                        "content_type": attachment.content_type,
                        "size": attachment.size,
                    }
                )

        try:
            message_id = self.db.store_message(
                channel_id=channel_id,
                discord_message_id=discord_message_id,
                user_id=user_id,
                username=username,
                content=content,
                timestamp=timestamp,
                attachments=attachments if attachments else None,
            )

            logger.debug(f"Stored message {discord_message_id} from {username} in channel {channel_id}")

            # Periodic cleanup check
            self.maybe_cleanup_channel(channel_id)

            # Check database size periodically
            self.maybe_cleanup_database_size()

            return message_id

        except Exception as e:
            logger.error(f"Failed to store message {discord_message_id}: {e}")
            raise

    def get_recent_messages(self, channel_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get recent messages from a channel for AI context

        Args:
            channel_id: Discord channel ID (string)
            limit: Number of recent messages to retrieve

        Returns:
            List of message dictionaries in chronological order
        """
        try:
            messages = self.db.get_recent_messages(channel_id, limit)
            logger.debug(f"Retrieved {len(messages)} messages from channel {channel_id}")
            return messages
        except Exception as e:
            logger.error(f"Failed to get messages from channel {channel_id}: {e}")
            return []

    def get_messages_by_date_range(
        self, channel_id: str, start_date: datetime, end_date: datetime
    ) -> list[dict[str, Any]]:
        """
        Get messages within a specific date range

        Args:
            channel_id: Discord channel ID (string)
            start_date: Start of date range (inclusive)
            end_date: End of date range (exclusive)

        Returns:
            List of message dictionaries in chronological order
        """
        try:
            messages = self.db.get_messages_by_date_range(channel_id, start_date, end_date)
            logger.debug(
                f"Retrieved {len(messages)} messages from channel {channel_id} between {start_date} and {end_date}"
            )
            return messages
        except Exception as e:
            logger.error(f"Failed to get messages by date range from channel {channel_id}: {e}")
            return []

    def delete_recent_messages(self, channel_id: str, limit: int) -> int:
        """
        Delete the most recent N messages from a channel

        Args:
            channel_id: Discord channel ID (string)
            limit: Number of recent messages to delete

        Returns:
            Number of messages deleted
        """
        try:
            deleted_count = self.db.delete_recent_messages(channel_id, limit)
            logger.info(f"Deleted {deleted_count} recent messages from channel {channel_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete messages from channel {channel_id}: {e}")
            return 0

    def delete_all_channel_messages(self, channel_id: str) -> int:
        """
        Delete ALL messages from a channel and remove conversation record

        Args:
            channel_id: Discord channel ID (string)

        Returns:
            Number of messages deleted
        """
        try:
            deleted_count = self.db.delete_all_channel_messages(channel_id)
            logger.info(
                f"Deleted ALL {deleted_count} messages from channel {channel_id} and removed conversation record"
            )
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete all messages from channel {channel_id}: {e}")
            return 0

    def maybe_cleanup_channel(self, channel_id: str):
        try:
            message_count = self.db.get_message_count(channel_id)

            # Only cleanup if we exceed the limit by a reasonable margin
            if message_count > MAX_MESSAGES_PER_CHANNEL + MESSAGES_CLEANUP_MARGIN:
                logger.info(f"Cleaning up channel {channel_id}: {message_count} messages")
                self.db.cleanup_old_messages(channel_id, MAX_MESSAGES_PER_CHANNEL)

        except Exception as e:
            logger.error(f"Failed to cleanup channel {channel_id}: {e}")

    def maybe_cleanup_database_size(self):
        """
        Check database size and cleanup if needed
        Only runs once per hour to avoid performance impact
        """
        now = datetime.now()
        if (now - self.last_size_check) < self.size_check_interval:
            return

        self.last_size_check = now

        try:
            current_size_mb = self.db.get_database_size_mb()
            logger.debug(f"Database size check: {current_size_mb:.1f}MB")

            if current_size_mb > (MAX_DATABASE_SIZE_GB * MB_PER_GB):
                logger.warning(f"Database size ({current_size_mb:.1f}MB) approaching limit, starting cleanup")
                self.db.cleanup_if_database_too_large(MAX_DATABASE_SIZE_GB)

        except Exception as e:
            logger.error(f"Failed to check database size: {e}")

    def get_database_info(self) -> dict[str, Any]:
        """Get current database information"""
        try:
            return {
                "size_mb": self.db.get_database_size_mb(),
                "total_messages": self.db.get_total_message_count(),
                "path": self.db_path,
            }
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}

    def get_conversation_stats(self) -> list[dict[str, Any]]:
        """
        Get statistics for all tracked conversations

        Returns:
            List of conversation stats
        """
        try:
            return self.db.get_channels_with_messages()
        except Exception as e:
            logger.error(f"Failed to get conversation stats: {e}")
            return []

    def format_messages_for_ai(self, messages: list[dict[str, Any]]) -> str:
        """
        Format messages for AI context

        Args:
            messages: List of message dictionaries from database

        Returns:
            Formatted message string
        """
        if not messages:
            return "No recent messages found."

        formatted_lines = []
        for msg in messages:
            timestamp = msg["timestamp"]
            username = msg["username"]
            content = msg["content"]

            # Format timestamp
            if isinstance(timestamp, str):
                # Parse ISO format timestamp
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    time_str = dt.strftime("%H:%M")
                except Exception:
                    time_str = timestamp[:5]  # Fallback to first 5 chars
            else:
                time_str = timestamp.strftime("%H:%M")

            # Add media info if present
            media_info = ""
            if msg.get("has_attachments") and msg.get("media_files"):
                media_count = len(msg["media_files"])
                media_info = f" [+{media_count} file{'s' if media_count > 1 else ''}]"

            formatted_lines.append(f"[{time_str}] {username}: {content}{media_info}")

        return "\n".join(formatted_lines)
