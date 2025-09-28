# Example: How Message Storage Works

from src.database import MessageDatabase
from datetime import datetime

# Initialize database
db = MessageDatabase("data/conversations.db")

## Example 1: Storing a simple text message
message_id = db.store_message(
    channel_id="123456789",
    discord_message_id="987654321", 
    user_id="555666777",
    username="tarquin_dan",
    content="Hello everyone!",
    timestamp=datetime.now()
)
print(f"Stored message with ID: {message_id}")

## Example 2: Storing a message with attachments
attachments = [
    {
        'filename': 'funny_meme.jpg',
        'url': 'https://cdn.discordapp.com/attachments/123/456/funny_meme.jpg',
        'content_type': 'image/jpeg',
        'size': 245760
    },
    {
        'filename': 'document.pdf', 
        'url': 'https://cdn.discordapp.com/attachments/123/456/document.pdf',
        'content_type': 'application/pdf',
        'size': 1048576
    }
]

message_id = db.store_message(
    channel_id="123456789",
    discord_message_id="987654322",
    user_id="888999000", 
    username="jorgen3604",
    content="Check out this meme and document!",
    timestamp=datetime.now(),
    attachments=attachments
)

## Example 3: Retrieving recent messages for AI context
recent_messages = db.get_recent_messages("123456789", limit=5)

print("Recent conversation context:")
for msg in recent_messages:
    timestamp = msg['timestamp']
    username = msg['username'] 
    content = msg['content']
    
    print(f"[{timestamp}] {username}: {content}")
    
    if msg['has_attachments']:
        for media in msg['media_files']:
            print(f"  📎 {media['filename']} ({media['content_type']})")

## Example 4: Database maintenance
print(f"Total messages in channel: {db.get_message_count('123456789')}")

# Clean up old messages (keep last 1000)
db.cleanup_old_messages("123456789", keep_last=1000)

## Example 5: Get overview of all channels
channels = db.get_channels_with_messages()
print("\nAll channels with messages:")
for channel in channels:
    print(f"Channel {channel['channel_id']}: {channel['message_count']} messages")