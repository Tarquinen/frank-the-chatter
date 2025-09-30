import discord
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv("../.env")

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables")

class MessageListener(discord.Client):
    async def on_ready(self):
        print(f'Bot logged in as {self.user}!')
        print(f'Listening for messages across all accessible channels')
        
    async def on_message(self, message):
        if message.author == self.user:
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        author = f"{message.author.display_name} (@{message.author.name})"
        channel_info = f"#{message.channel.name}" if hasattr(message.channel, 'name') else f"Channel {message.channel.id}"
        content = message.content
        
        if message.attachments:
            for attachment in message.attachments:
                content += f" [Image: {attachment.url}]"
        
        log_entry = f"[{timestamp}] {channel_info} {author}: {content}"
        print(log_entry)
        
        with open("../data/logs/message_log.txt", "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

client = MessageListener()
client.run(TOKEN)