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

        self.command_handler = CommandHandler(self.message_storage, self.ai_client)
        logger.info("Command handler initialized")

        self.random_reply_task = None

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
            self.command_handler.set_bot(self)
            self.random_reply_task = asyncio.create_task(self._random_reply_scheduler())
            logger.info("Random reply scheduler started")

    async def on_message(self, message):
        await self._store_message(message)

        if message.author == self.user:
            return

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

                    if "execute_after_send" in command_result:
                        await command_result["execute_after_send"](message, sent_message)

                    return

            recent_messages = self.message_storage.get_recent_messages(channel_id, MAX_MESSAGE_CONTEXT_FOR_AI)

            logger.info(f"Bot mentioned in {getattr(message.channel, 'name', 'DM')} by {message.author.display_name}")
            logger.info(f"Available context: {len(recent_messages)} messages from database")
            # Generate AI response
            try:
                ai_response = await self.ai_client.generate_response(
                    context_messages=recent_messages,
                    mentioned_by=message.author.display_name,
                )

                if ai_response:
                    await message.channel.send(ai_response)
                else:
                    # Fallback response if AI fails
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

    async def _random_reply_scheduler(self):
        """
        Background task that executes random replies twice per day
        Runs at random times roughly 12 hours apart
        """
        logger.info("Random reply scheduler initialized")

        while True:
            try:
                hours_until_next = random.uniform(10, 14)
                seconds_until_next = hours_until_next * 3600
                logger.info(f"Next random reply scheduled in {hours_until_next:.1f} hours")

                await asyncio.sleep(seconds_until_next)

                logger.info("Executing scheduled random reply")
                await self.random_reply.execute_random_reply()

            except asyncio.CancelledError:
                logger.info("Random reply scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in random reply scheduler: {e}", exc_info=True)
                await asyncio.sleep(3600)


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
