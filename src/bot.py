"""Main Discord bot entry point for Frank the Chatter"""

import asyncio
from pathlib import Path
import random
import sys

import discord

from utils.config import Config
from utils.logger import setup_logger

sys.path.append(str(Path(__file__).parent))

from ai_client import AIClient
from commands import CommandHandler
from message_storage import MessageStorage
from utils.constants import (
    LOG_MESSAGE_PREVIEW_LENGTH,
    MAX_MESSAGE_CONTEXT_FOR_AI,
    TOP_CHANNELS_TO_SHOW,
)

# Validate configuration
Config.validate()

# Setup logging
logger = setup_logger()


class FrankBot(discord.Client):
    def __init__(self):
        super().__init__()

        self.message_storage = MessageStorage()
        logger.info("Database storage initialized")

        self.ai_client = AIClient()

        if Config.ENABLE_PERSONALITY_FEATURE:
            from personality_manager import PersonalityManager

            self.personality_manager = PersonalityManager(Config.DATABASE_PATH)
            logger.info("Personality manager initialized")
        else:
            self.personality_manager = None

        self.command_handler = CommandHandler(
            self.message_storage, self.ai_client, personality_manager=self.personality_manager
        )
        logger.info("Command handler initialized")

        self.random_reply_task = None
        self.random_react_task = None
        self.channel_cleanup_task = None
        self.channel_message_counts = {}

    async def on_ready(self):
        """Called when bot connects successfully"""
        if self.user is None:
            logger.error("Bot user is None after connecting")
            return

        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Bot is connected to {len(self.guilds)} servers")

        for guild in self.guilds:
            logger.info(f"Connected to server: {guild.name} (ID: {guild.id})")

        stats = self.message_storage.get_conversation_stats()
        db_info = self.message_storage.get_database_info()
        logger.info(f"Database contains {len(stats)} tracked conversations")
        logger.info(
            f"Database size: {db_info.get('size_mb', 0):.1f}MB, Total messages: {db_info.get('total_messages', 0)}"
        )
        for stat in stats[:TOP_CHANNELS_TO_SHOW]:
            channel_name = stat.get("channel_name", "Unknown")
            logger.info(f"  Channel {channel_name} ({stat['channel_id']}): {stat['message_count']} messages")

        if self.random_reply_task is None:
            from commands.random_reply import RandomReply

            self.random_reply = RandomReply(self, self.message_storage, self.ai_client)
            self.random_reply_task = asyncio.create_task(self._random_reply_scheduler())
            logger.info("Random reply scheduler started")

        if self.random_react_task is None:
            from commands.random_react import RandomReact

            self.random_react = RandomReact(self, self.message_storage, self.ai_client)
            logger.info("Random react initialized (triggers every 10 messages per channel)")

        if self.channel_cleanup_task is None:
            asyncio.create_task(self._cleanup_inaccessible_channels())  # noqa: RUF006
            self.channel_cleanup_task = asyncio.create_task(self._channel_cleanup_scheduler())
            logger.info("Channel cleanup running on startup and scheduled for every 24 hours")

        self.command_handler.set_bot(self)

    async def on_message(self, message):
        await self._store_message(message)

        if message.author == self.user:
            return

        channel_id = str(message.channel.id)
        self.channel_message_counts[channel_id] = self.channel_message_counts.get(channel_id, 0) + 1

        if self.channel_message_counts[channel_id] >= 10:
            self.channel_message_counts[channel_id] = 0
            if hasattr(self, "random_react"):
                task = asyncio.create_task(self.random_react.execute_random_react(message.channel))
                task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)

        if self.user and self.user.mentioned_in(message):
            await self._handle_mention(message)

    async def _store_message(self, message):
        try:
            self.message_storage.store_message(message)

            channel_name = getattr(message.channel, "name", f"Channel-{message.channel.id}")
            preview = message.content[:LOG_MESSAGE_PREVIEW_LENGTH]
            overflow = "..." if len(message.content) > LOG_MESSAGE_PREVIEW_LENGTH else ""
            log_msg = f"[{channel_name}] {message.author.display_name}: {preview}{overflow}"
            if message.attachments:
                log_msg += f" [{len(message.attachments)} attachment(s)]"
            logger.debug(log_msg)

        except Exception as e:
            logger.error(f"Failed to store message: {e}")

    async def _handle_mention(self, message):
        """Handle when bot is mentioned - now with AI integration and commands"""
        channel_id = str(message.channel.id)

        # Show typing indicator immediately
        async with message.channel.typing():
            # Check for commands first
            parsed_command = self.command_handler.parse_command(message.content)
            if parsed_command:
                command_name, args = parsed_command
                logger.info(
                    f"Command detected: !{command_name} by {message.author.display_name} (ID: {message.author.id})"
                )

                command_result = await self.command_handler.handle_command(message, command_name, args)
                if command_result:
                    sent_message = await message.channel.send(command_result["response"])

                    if "personality_changes" in command_result and self.personality_manager:
                        personality_changes = command_result["personality_changes"]
                        if personality_changes:
                            user_id = str(message.author.id)
                            username = message.author.display_name
                            updates = personality_changes.get("updates", [])
                            deletions = personality_changes.get("deletions", [])

                            self.personality_manager.update_user_personality(user_id, username, updates, deletions)

                            log_parts = []
                            if updates:
                                log_parts.append(f"added {len(updates)} new points")
                            if deletions:
                                log_parts.append(f"deleted {len(deletions)} points")
                            if log_parts:
                                logger.info(f"Updated personality for {username}: {', '.join(log_parts)}")

                    if "execute_after_send" in command_result:
                        await command_result["execute_after_send"](message, sent_message)

                    return

            recent_messages = self.message_storage.get_recent_messages(channel_id, MAX_MESSAGE_CONTEXT_FOR_AI)

            logger.info(f"Bot mentioned in {getattr(message.channel, 'name', 'DM')} by {message.author.display_name}")
            logger.info(f"Available context: {len(recent_messages)} messages from database")

            user_personality = None
            if self.personality_manager:
                user_id = str(message.author.id)
                user_personality = self.personality_manager.get_user_personality(user_id)
                if user_personality:
                    point_count = len(user_personality.get("points", []))
                    logger.info(f"Loaded personality for {message.author.display_name}: {point_count} points")

            try:
                ai_response, personality_changes = await self.ai_client.generate_response(
                    context_messages=recent_messages,
                    mentioned_by=message.author.display_name,
                    user_personality=user_personality,
                )

                if self.personality_manager and personality_changes:
                    user_id = str(message.author.id)
                    username = message.author.display_name
                    updates = personality_changes.get("updates", [])
                    deletions = personality_changes.get("deletions", [])

                    self.personality_manager.update_user_personality(user_id, username, updates, deletions)

                    log_parts = []
                    if updates:
                        log_parts.append(f"added {len(updates)} new points")
                    if deletions:
                        log_parts.append(f"deleted {len(deletions)} points")
                    if log_parts:
                        logger.info(f"Updated personality for {username}: {', '.join(log_parts)}")

                if ai_response:
                    await message.channel.send(ai_response)
                else:
                    await message.channel.send(
                        f"Hi {message.author.mention}! I heard you mention me. "
                        f"I have {len(recent_messages)} messages of context stored. "
                        f"My AI is having trouble right now, but I'm still here!"
                    )
            except Exception as e:
                logger.error(f"Error handling mention: {e}")
                await message.channel.send(
                    f"Hi {message.author.mention}! Something went wrong, but I'm still logging our conversation!"
                )

        # Note: Bot's response will be automatically stored when on_message fires for it

    async def _scheduled_task(self, task_name: str, execute_func, min_hours: float, max_hours: float):
        """
        Generic background task scheduler that executes a function at random intervals

        Args:
            task_name: Name of the task for logging
            execute_func: Async function to execute
            min_hours: Minimum hours between executions
            max_hours: Maximum hours between executions
        """
        logger.info(f"{task_name} scheduler initialized")

        while True:
            try:
                hours_until_next = random.uniform(min_hours, max_hours)
                seconds_until_next = hours_until_next * 3600
                logger.info(f"Next {task_name} scheduled in {hours_until_next:.1f} hours")

                await asyncio.sleep(seconds_until_next)

                logger.info(f"Executing scheduled {task_name}")
                await execute_func()

            except asyncio.CancelledError:
                logger.info(f"{task_name} scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in {task_name} scheduler: {e}", exc_info=True)
                await asyncio.sleep(3600)

    async def _random_reply_scheduler(self):
        """Background task that executes random replies twice per day (10-14 hour intervals)"""
        await self._scheduled_task("random reply", self.random_reply.execute_random_reply, 10, 14)

    async def _channel_cleanup_scheduler(self):
        """Background task that cleans up inaccessible channels once per day"""
        await self._scheduled_task("channel cleanup", self._cleanup_inaccessible_channels, 24, 24)

    async def _cleanup_inaccessible_channels(self):
        """Clean up channels from database that Frank no longer has access to"""
        try:
            accessible_channel_ids = []

            for guild in self.guilds:
                for channel in guild.channels:
                    accessible_channel_ids.append(str(channel.id))

            for channel in self.private_channels:
                accessible_channel_ids.append(str(channel.id))

            logger.info(f"Found {len(accessible_channel_ids)} accessible channels across {len(self.guilds)} guilds")

            cleaned_count = self.message_storage.cleanup_inaccessible_channels(accessible_channel_ids)

            if cleaned_count > 0:
                logger.info(f"Successfully cleaned up {cleaned_count} inaccessible channels")
            else:
                logger.info("No inaccessible channels found to clean up")

        except Exception as e:
            logger.error(f"Error cleaning up inaccessible channels: {e}", exc_info=True)


def main():
    """Main entry point with auto-reconnect"""
    logger.info("Starting Frank the Chatter bot...")

    if not Config.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not found in environment")
        return

    reconnect_delay = 5

    while True:
        try:
            bot = FrankBot()
            bot.run(Config.DISCORD_TOKEN, reconnect=True)
        except KeyboardInterrupt:
            logger.info("Bot shutdown requested by user")
            break
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            logger.info(f"Attempting to reconnect in {reconnect_delay} seconds...")
            import time

            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 300)


if __name__ == "__main__":
    main()
