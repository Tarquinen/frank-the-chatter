import discord
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID not found in environment variables")

CHANNEL_ID = int(CHANNEL_ID)

class MessageListener(discord.Client):
    async def on_ready(self):
        print(f'Bot logged in as {self.user}!')
        print(f'Listening for messages in channel ID: {CHANNEL_ID}')
        
    async def on_message(self, message):
        if message.channel.id == CHANNEL_ID:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            author = message.author.name
            content = message.content
            
            log_entry = f"[{timestamp}] {author}: {content}"
            print(log_entry)
            
            with open("message_log.txt", "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")

client = MessageListener()
client.run(TOKEN)