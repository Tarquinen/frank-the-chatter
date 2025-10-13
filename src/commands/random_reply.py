import re

import discord

from utils.config import PROMPT_DIR, Config
from utils.constants import AI_RANDOM_REPLY_MAX_TOKENS, MAX_MESSAGE_CONTEXT_FOR_AI
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RandomReply:
    def __init__(self, bot, message_storage, ai_client):
        self.name = "random_reply"
        self.requires_auth = True
        self.bot = bot
        self.message_storage = message_storage
        self.ai_client = ai_client
        self.prompt = self._load_prompt()

    async def execute(self, _message, _args) -> str:
        try:
            await self.execute_random_reply()
            return "Random reply triggered successfully! Check the logs for details."
        except Exception as e:
            return f"Error triggering random reply: {e}"

    async def execute_random_reply(self):
        try:
            logger.info("Starting random reply execution")

            exclude_user_ids = [
                str(Config.BOT_USER_ID),
                str(Config.DAN_USER_ID),
            ]

            random_user = self.message_storage.db.get_random_user(exclude_user_ids)

            if not random_user:
                logger.warning("No eligible users found for random reply")
                return

            user_id = random_user["user_id"]
            username = random_user["username"]
            channel_id = random_user["channel_id"]

            logger.info(f"Selected user {username} (ID: {user_id}) in channel {channel_id}")

            messages = self.message_storage.db.get_user_messages_with_ids(
                user_id=user_id, channel_id=channel_id, limit=MAX_MESSAGE_CONTEXT_FOR_AI
            )

            if not messages:
                logger.warning(f"No messages found for user {username}")
                return

            logger.info(f"Retrieved {len(messages)} messages from {username}")

            ai_response = await self._generate_reply_with_selection(username, messages)

            if not ai_response:
                logger.error("AI failed to generate a response")
                return

            target_message_id, reply_text = self._parse_ai_response(ai_response)

            if not target_message_id or not reply_text:
                logger.error(f"Failed to parse AI response: {ai_response[:200]}")
                return

            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Could not find channel {channel_id}")
                return

            try:
                target_message = await channel.fetch_message(int(target_message_id))
            except discord.NotFound:
                logger.error(f"Message {target_message_id} not found in channel")
                return
            except discord.Forbidden:
                logger.error(f"No permission to fetch message {target_message_id}")
                return

            await target_message.reply(reply_text)
            logger.info(f"Successfully replied to message {target_message_id} from {username}")

        except Exception as e:
            logger.error(f"Error in random reply execution: {e}", exc_info=True)

    async def _generate_reply_with_selection(self, username: str, messages: list[dict]) -> str | None:
        try:
            if not self.ai_client.is_available():
                logger.error("AI client is not available")
                return None

            prompt = self.prompt

            context_parts = [f"Messages from {username}:\n"]
            for msg in messages:
                message_id = msg["discord_message_id"]
                content = msg["content"]
                context_parts.append(f"[ID: {message_id}] {username}: {content}")

            formatted_context = "\n".join(context_parts)

            ai_response = await self.ai_client._generate_with_config(
                formatted_context=formatted_context,
                system_prompt=prompt,
                image_urls=None,
                enable_tools=False,
                temperature=1.0,
                max_tokens=AI_RANDOM_REPLY_MAX_TOKENS,
            )

            return ai_response

        except Exception as e:
            logger.error(f"Error generating reply: {e}")
            return None

    def _load_prompt(self) -> str:
        try:
            prompt_path = PROMPT_DIR / "random_reply.txt"
            if prompt_path.exists():
                return prompt_path.read_text().strip()
            else:
                logger.warning("random_reply.txt not found, using default prompt")
                return (
                    "You are Frank, a witty AI. Select the most interesting message and reply to it. "
                    "Format: REPLY_TO: [message_id]\\n[your response]"
                )
        except Exception as e:
            logger.error(f"Error loading random reply prompt: {e}")
            return (
                "You are Frank, a witty AI. Select the most interesting message and reply to it. "
                "Format: REPLY_TO: [message_id]\\n[your response]"
            )

    def _parse_ai_response(self, response: str) -> tuple[str | None, str | None]:
        match = re.match(r"REPLY_TO:\s*(\d+)\s*\n(.*)", response, re.DOTALL)
        if match:
            message_id = match.group(1).strip()
            reply_text = match.group(2).strip()
            return message_id, reply_text
        return None, None
