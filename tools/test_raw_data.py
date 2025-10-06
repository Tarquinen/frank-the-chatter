"""Test to see what raw data Discord provides"""

from pathlib import Path
import sys

import discord

sys.path.append(str(Path(__file__).parent.parent / 'src'))
import json

from utils.config import Config
from utils.logger import setup_logger

logger = setup_logger()

class RawDataBot(discord.Client):
    async def on_socket_response(self, msg):
        if msg.get('t') == 'MESSAGE_CREATE':
            author_data = msg.get('d', {}).get('author', {})
            if 'global_name' in author_data:
                logger.info("\n=== Found global_name in raw data! ===")
                logger.info(f"Username: {author_data.get('username')}")
                logger.info(f"Global Name: {author_data.get('global_name')}")
                logger.info(f"Full author data: {json.dumps(author_data, indent=2)}")

if __name__ == "__main__":
    Config.validate()
    bot = RawDataBot()
    bot.run(Config.DISCORD_TOKEN)
