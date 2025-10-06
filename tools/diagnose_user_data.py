"""Diagnostic to see raw Discord API data"""

import discord
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))
from utils.config import Config
from utils.logger import setup_logger
import json

logger = setup_logger()

class DiagnosticBot(discord.Client):
    def __init__(self):
        super().__init__(enable_debug_events=True)
        
    async def on_ready(self):
        logger.info(f"Bot ready as {self.user}")
        logger.info("Send a DM to see what data Discord provides...")
        
    async def on_socket_raw_receive(self, msg):
        try:
            if isinstance(msg, bytes):
                return
            data = json.loads(msg)
            if data.get('t') == 'MESSAGE_CREATE':
                author = data.get('d', {}).get('author', {})
                logger.info(f"\n=== RAW MESSAGE_CREATE AUTHOR DATA ===")
                logger.info(json.dumps(author, indent=2))
                logger.info(f"\nKeys available: {list(author.keys())}")
                logger.info(f"Username: {author.get('username')}")
                logger.info(f"Global name: {author.get('global_name')}")
                logger.info(f"Discriminator: {author.get('discriminator')}")
        except Exception as e:
            logger.error(f"Error in socket handler: {e}")
    
    async def on_message(self, message):
        if message.author == self.user:
            return
        logger.info(f"\n=== PARSED MESSAGE OBJECT ===")
        logger.info(f"message.author type: {type(message.author)}")
        logger.info(f"message.author.__class__.__name__: {message.author.__class__.__name__}")
        logger.info(f"message.author.name: {message.author.name}")
        logger.info(f"message.author.display_name: {message.author.display_name}")
        logger.info(f"message.author.discriminator: {message.author.discriminator}")
        logger.info(f"Has global_name attr: {hasattr(message.author, 'global_name')}")
        logger.info(f"message.author.__slots__: {message.author.__slots__ if hasattr(message.author, '__slots__') else 'No slots'}")
        logger.info(f"dir(message.author): {[a for a in dir(message.author) if 'global' in a.lower()]}")
        try:
            gn = getattr(message.author, 'global_name', 'ATTRIBUTE_NOT_FOUND')
            logger.info(f"getattr global_name: {gn}")
        except Exception as e:
            logger.info(f"Error getting global_name: {e}")

if __name__ == "__main__":
    Config.validate()
    bot = DiagnosticBot()
    bot.run(Config.DISCORD_TOKEN)
