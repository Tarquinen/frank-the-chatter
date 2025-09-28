"""Main Discord bot entry point for Frank the Chatter"""

import discord
from utils.config import Config
from utils.logger import setup_logger

# Validate configuration
Config.validate()

# Setup logging
logger = setup_logger()

class FrankBot(discord.Client):
    def __init__(self):
        # Set up intents for message content and guild messages
        # intents = discord.Intents.default()
        # intents.message_content = True
        # intents.guilds = True
        
        super().__init__()
        
        # In-memory storage for active conversations (Phase 1)
        self.conversations = {}  # channel_id -> list of recent messages
        
    async def on_ready(self):
        """Called when bot connects successfully"""
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Bot is connected to {len(self.guilds)} servers")
        
        # Log server information
        for guild in self.guilds:
            logger.info(f"Connected to server: {guild.name} (ID: {guild.id})")
            
    async def on_message(self, message):
        """Handle incoming messages"""
        # Store all messages in memory (including bot's own messages)
        await self._store_message(message)
        
        # Don't process bot's own messages for mentions
        if message.author == self.user:
            return
        
        # Check if bot is mentioned
        if self.user.mentioned_in(message):
            await self._handle_mention(message)
            
    async def _store_message(self, message):
        """Store message in in-memory conversation storage"""
        channel_id = str(message.channel.id)
        
        # Initialize conversation if not exists
        if channel_id not in self.conversations:
            self.conversations[channel_id] = []
            
        # Create message data
        message_data = {
            'id': str(message.id),
            'author': message.author.name,
            'author_id': str(message.author.id), 
            'content': message.content,
            'timestamp': message.created_at,
            'attachments': [att.url for att in message.attachments] if message.attachments else []
        }
        
        # Add to conversation
        self.conversations[channel_id].append(message_data)
        
        # Keep only last 1000 messages per channel
        if len(self.conversations[channel_id]) > Config.MAX_MESSAGES_PER_CONVERSATION:
            self.conversations[channel_id] = self.conversations[channel_id][-Config.MAX_MESSAGES_PER_CONVERSATION:]
            
        # Log message
        channel_name = getattr(message.channel, 'name', f'Channel-{message.channel.id}')
        log_msg = f"[{channel_name}] {message.author.name}: {message.content[:100]}{'...' if len(message.content) > 100 else ''}"
        if message.attachments:
            log_msg += f" [{len(message.attachments)} attachment(s)]"
        logger.info(log_msg)
        
    async def _handle_mention(self, message):
        """Handle when bot is mentioned - placeholder for AI integration"""
        channel_id = str(message.channel.id)
        
        # Get recent messages for context
        recent_messages = self.conversations.get(channel_id, [])
        context_messages = recent_messages[-Config.MAX_MESSAGE_CONTEXT_FOR_AI:]
        
        logger.info(f"Bot mentioned in {getattr(message.channel, 'name', 'DM')} by {message.author.name}")
        logger.info(f"Available context: {len(context_messages)} messages")
        
        # Placeholder response (will be replaced with AI integration in Phase 3)
        await message.channel.send(f"Hi {message.author.mention}! I heard you mention me. I have {len(context_messages)} messages of context from this conversation. AI integration coming in Phase 3!")
        
        # Note: Bot's response will be automatically stored when on_message fires for it

def main():
    """Main entry point"""
    logger.info("Starting Frank the Chatter bot...")
    
    try:
        bot = FrankBot()
        bot.run(Config.DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()
