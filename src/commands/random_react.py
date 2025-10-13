import re

import discord

from utils.config import PROMPT_DIR, Config
from utils.constants import AI_RANDOM_REPLY_MAX_TOKENS, MAX_MESSAGE_CONTEXT_FOR_AI
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RandomReact:
    def __init__(self, bot, message_storage, ai_client):
        self.name = "random_react"
        self.requires_auth = True
        self.bot = bot
        self.message_storage = message_storage
        self.ai_client = ai_client
        self.prompt = self._load_prompt()

    async def execute(self, _message, _args) -> str:
        try:
            await self.execute_random_react()
            return "Random react triggered successfully! Check the logs for details."
        except Exception as e:
            return f"Error triggering random react: {e}"

    async def execute_random_react(self):
        try:
            logger.info("Starting random react execution")

            random_user = self.message_storage.db.get_random_user(
                exclude_user_ids=[str(Config.BOT_USER_ID)], include_bot_interactions=True
            )

            if not random_user:
                logger.warning("No eligible users found for random react")
                return

            user_id = random_user["user_id"]
            username = random_user["username"]
            channel_id = random_user["channel_id"]

            logger.info(f"Selected user {username} (ID: {user_id}) in channel {channel_id}")

            messages = self.message_storage.db.get_user_messages_with_ids(
                user_id=user_id, channel_id=channel_id, limit=MAX_MESSAGE_CONTEXT_FOR_AI, include_bot_interactions=True
            )

            if not messages:
                logger.warning(f"No messages found for user {username}")
                return

            logger.info(f"Retrieved {len(messages)} messages from {username}")

            ai_response = await self._generate_react_with_selection(username, messages)

            if not ai_response:
                logger.error("AI failed to generate a response")
                return

            logger.info(f"AI response: {ai_response}")

            target_message_id, emoji = self._parse_ai_response(ai_response)

            if not target_message_id or not emoji:
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

            try:
                await target_message.add_reaction(emoji)
                logger.info(f"Successfully reacted with {emoji} to message {target_message_id} from {username}")
            except discord.HTTPException as e:
                logger.error(f"Failed to add reaction {emoji}: {e}")
                return

        except Exception as e:
            logger.error(f"Error in random react execution: {e}", exc_info=True)

    async def _generate_react_with_selection(self, username: str, messages: list[dict]) -> str | None:
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
            logger.error(f"Error generating react: {e}")
            return None

    def _load_prompt(self) -> str:
        try:
            prompt_path = PROMPT_DIR / "random_react.txt"
            if prompt_path.exists():
                return prompt_path.read_text().strip()
            else:
                logger.warning("random_react.txt not found, using default prompt")
                return (
                    "You are Frank. Pick a single emoji that best reacts to this message. "
                    "Respond with ONLY the emoji character, nothing else."
                )
        except Exception as e:
            logger.error(f"Error loading random react prompt: {e}")
            return (
                "You are Frank. Pick a single emoji that best reacts to this message. "
                "Respond with ONLY the emoji character, nothing else."
            )

    def _parse_ai_response(self, response: str) -> tuple[str | None, str | None]:
        match = re.match(r"REACT_TO:\s*(\d+)\s*\n\s*(.+)", response, re.DOTALL)
        if match:
            message_id = match.group(1).strip()
            emoji_line = match.group(2).strip()

            emoji = ""
            for char in emoji_line:
                if ord(char) > 127:
                    emoji += char
                elif char.isspace():
                    break

            if not emoji:
                emoji = emoji_line.split()[0] if emoji_line else ""

            return message_id, emoji
        return None, None
