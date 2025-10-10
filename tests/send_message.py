import os

import discord
from dotenv import load_dotenv

load_dotenv("../.env")

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is required")
if CHANNEL_ID == 0:
    raise ValueError("CHANNEL_ID environment variable is required")


class MyClient(discord.Client):
    async def on_ready(self):
        print(f"Logged on as {self.user}!")

        channel = self.get_channel(CHANNEL_ID)

        if channel:
            print("Found channel. Sending message...")
            await channel.send("sending a message from a bot")
            print("Message sent!")
        else:
            print(f"Error: Could not find the channel with ID {CHANNEL_ID}.")
            print("Please make sure the ID is correct and you have access to the channel.")

        await self.close()


client = MyClient()
client.run(TOKEN)
