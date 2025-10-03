from typing import Optional
from utils.logger import setup_logger
from utils.config import Config

logger = setup_logger(__name__)


class BeHelpfulCommand:
    def __init__(self, message_storage, ai_client):
        self.name = "bh"
        self.requires_auth = False
        self.message_storage = message_storage
        self.ai_client = ai_client

    async def execute(self, message) -> str:
        try:
            channel_id = str(message.channel.id)

            recent_messages = self.message_storage.get_recent_messages(
                channel_id, Config.MAX_MESSAGE_CONTEXT_FOR_AI
            )

            logger.info(
                f"BeHelpful mode activated by {message.author.display_name} with {len(recent_messages)} messages of context"
            )

            if not self.ai_client.is_available():
                return f"Hi {message.author.mention}! My AI is currently unavailable."

            original_prompt = self.ai_client.system_prompt
            helpful_prompt = self.ai_client._load_system_prompt("helpful.txt")

            self.ai_client.system_prompt = helpful_prompt

            try:
                formatted_context, image_urls = self.ai_client._format_context_for_ai(
                    recent_messages, message.author.display_name
                )

                ai_response = await self.ai_client._generate_conversation_response(
                    formatted_context, image_urls
                )

                return (
                    ai_response
                    if ai_response
                    else f"Hi {message.author.mention}! I'm having trouble generating a response right now."
                )

            finally:
                self.ai_client.system_prompt = original_prompt

        except Exception as e:
            logger.error(f"Error in BeHelpfulCommand: {e}")
            return f"Hi {message.author.mention}! Something went wrong while trying to help."
