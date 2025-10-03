"""Main Discord bot entry point for Frank the Chatter"""

import discord
from utils.config import Config
from utils.logger import setup_logger
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from message_storage import MessageStorage
from ai_client import AIClient
from commands import CommandHandler

# Validate configuration
Config.validate()

# Setup logging
logger = setup_logger()


class FrankBot(discord.Client):
    def __init__(self):
        super().__init__()

        # Initialize database storage (Phase 2)
        self.message_storage = MessageStorage()
        logger.info("Database storage initialized")

        # Initialize AI client (Phase 3)
        self.ai_client = AIClient()

        # Initialize command handler
        self.command_handler = CommandHandler(self.message_storage, self.ai_client)
        logger.info("Command handler initialized")

    async def on_ready(self):
        """Called when bot connects successfully"""
        if self.user is None:
            logger.error("Bot user is None after connecting")
            return

        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Bot is connected to {len(self.guilds)} servers")

        # Log server information and conversation stats
        for guild in self.guilds:
            logger.info(f"Connected to server: {guild.name} (ID: {guild.id})")

        # Show conversation statistics from database
        stats = self.message_storage.get_conversation_stats()
        db_info = self.message_storage.get_database_info()
        logger.info(f"Database contains {len(stats)} tracked conversations")
        logger.info(
            f"Database size: {db_info.get('size_mb', 0):.1f}MB, Total messages: {db_info.get('total_messages', 0)}"
        )
        for stat in stats[:5]:  # Show top 5 active channels
            channel_name = stat.get("channel_name", "Unknown")
            logger.info(
                f"  Channel {channel_name} ({stat['channel_id']}): {stat['message_count']} messages"
            )

    async def on_message(self, message):
        """Handle incoming messages"""
        # Store all messages in database (including bot's own messages)
        await self._store_message(message)

        # Don't process bot's own messages for mentions
        if message.author == self.user:
            return

        # Check if bot is mentioned
        if self.user and self.user.mentioned_in(message):
            await self._handle_mention(message)

    async def _store_message(self, message):
        """Store message in database"""
        try:
            # Store message using MessageStorage
            message_id = self.message_storage.store_message(message)

            # Log message
            channel_name = getattr(
                message.channel, "name", f"Channel-{message.channel.id}"
            )
            log_msg = f"[{channel_name}] {message.author.display_name}: {message.content[:100]}{'...' if len(message.content) > 100 else ''}"
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

                command_result = await self.command_handler.handle_command(
                    message, command_name, args
                )
                if command_result:
                    sent_message = await message.channel.send(
                        command_result["response"]
                    )

                    if "execute_after_send" in command_result:
                        await command_result["execute_after_send"](
                            message, sent_message
                        )

                    return
            # Get recent messages from database for context
            recent_messages = self.message_storage.get_recent_messages(
                channel_id, Config.MAX_MESSAGE_CONTEXT_FOR_AI
            )

            logger.info(
                f"Bot mentioned in {getattr(message.channel, 'name', 'DM')} by {message.author.display_name}"
            )
            logger.info(
                f"Available context: {len(recent_messages)} messages from database"
            )
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


def main():
    """Main entry point"""
    logger.info("Starting Frank the Chatter bot...")

    if not Config.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not found in environment")
        return

    try:
        bot = FrankBot()
        bot.run(Config.DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    main()
