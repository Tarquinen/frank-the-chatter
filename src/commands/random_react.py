import re

import discord

from utils.config import PROMPT_DIR
from utils.constants import AI_RANDOM_REPLY_MAX_TOKENS
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
            channel = _message.channel
            await self.execute_random_react(channel)
            return "Random react triggered successfully! Check the logs for details."
        except Exception as e:
            return f"Error triggering random react: {e}"

    async def execute_random_react(self, channel):
        try:
            logger.info(f"Starting random react execution in channel {channel.id}")

            messages = []
            async for msg in channel.history(limit=20):
                if msg.author != self.bot.user:
                    messages.append(msg)

            if not messages:
                logger.warning(f"No messages found in channel {channel.id}")
                return

            logger.info(f"Retrieved {len(messages)} messages from channel {channel.id}")

            ai_response = await self._generate_react_with_selection(messages)

            if not ai_response:
                logger.error("AI failed to generate a response")
                return

            logger.info(f"AI response: {ai_response}")

            target_message_id, emoji = self._parse_ai_response(ai_response)

            if not target_message_id or not emoji:
                logger.error(f"Failed to parse AI response: {ai_response[:200]}")
                return

            target_message = None
            for msg in messages:
                if str(msg.id) == target_message_id:
                    target_message = msg
                    break

            if not target_message:
                logger.error(f"Message {target_message_id} not found in recent messages")
                return

            try:
                await target_message.add_reaction(emoji)
                logger.info(f"Successfully reacted with {emoji} to message {target_message_id}")
            except discord.HTTPException as e:
                logger.error(f"Failed to add reaction {emoji}: {e}")
                return

        except Exception as e:
            logger.error(f"Error in random react execution: {e}", exc_info=True)

    async def _generate_react_with_selection(self, messages: list[discord.Message]) -> str | None:
        try:
            if not self.ai_client.is_available():
                logger.error("AI client is not available")
                return None

            prompt = self.prompt

            context_parts = ["Recent messages in this channel:\n"]
            for msg in reversed(messages):
                message_id = msg.id
                username = msg.author.display_name
                content = msg.content or "[no text content]"

                reactions_str = ""
                if msg.reactions:
                    reaction_list = []
                    for reaction in msg.reactions:
                        reaction_list.append(f"{reaction.emoji}x{reaction.count}")
                    reactions_str = f" [Reactions: {', '.join(reaction_list)}]"

                context_parts.append(f"[ID: {message_id}] {username}: {content}{reactions_str}")

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
