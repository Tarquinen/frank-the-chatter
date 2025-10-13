from typing import Any

from utils.constants import MAX_MESSAGE_CONTEXT_FOR_AI
from utils.logger import setup_logger

logger = setup_logger(__name__)


class BeHelpfulCommand:
    def __init__(self, message_storage, ai_client, personality_manager=None):
        self.name = "bh"
        self.requires_auth = False
        self.message_storage = message_storage
        self.ai_client = ai_client
        self.personality_manager = personality_manager

    async def execute(self, message) -> str | dict[str, Any]:
        try:
            channel_id = str(message.channel.id)

            recent_messages = self.message_storage.get_recent_messages(channel_id, MAX_MESSAGE_CONTEXT_FOR_AI)

            logger.info(
                "BeHelpful mode activated by %s with %d messages of context",
                message.author.display_name,
                len(recent_messages),
            )

            if not self.ai_client.is_available():
                return f"Hi {message.author.mention}! My AI is currently unavailable."

            user_personality = None
            if self.personality_manager:
                user_id = str(message.author.id)
                user_personality = self.personality_manager.get_user_personality(user_id)
                if user_personality:
                    point_count = len(user_personality.get("points", []))
                    logger.info(f"Loaded personality for {message.author.display_name}: {point_count} points")

            original_prompt = self.ai_client.system_prompt
            original_personality_prompt = self.ai_client.personality_prompt
            helpful_prompt = self.ai_client._load_system_prompt("helpful.txt")

            self.ai_client.system_prompt = helpful_prompt
            self.ai_client.personality_prompt = self.ai_client._load_system_prompt("personality.txt")

            try:
                formatted_context, image_urls = self.ai_client._format_context_for_ai(
                    recent_messages, message.author.display_name, user_personality
                )

                ai_response = await self.ai_client._generate_conversation_response(formatted_context, image_urls)

                if ai_response:
                    clean_response, personality_changes = self.ai_client._parse_personality_changes(ai_response)
                    return {"response": clean_response, "personality_changes": personality_changes}
                else:
                    return f"Hi {message.author.mention}! I'm having trouble generating a response right now."

            finally:
                self.ai_client.system_prompt = original_prompt
                self.ai_client.personality_prompt = original_personality_prompt

        except Exception as e:
            logger.error(f"Error in BeHelpfulCommand: {e}")
            return f"Hi {message.author.mention}! Something went wrong while trying to help."
