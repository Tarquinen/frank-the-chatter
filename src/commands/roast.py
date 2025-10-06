import discord

from utils.config import Config
from utils.constants import MAX_MESSAGE_CONTEXT_FOR_AI
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RoastCommand:
    def __init__(self, message_storage, ai_client):
        self.name = "roast"
        self.requires_auth = False
        self.message_storage = message_storage
        self.ai_client = ai_client

    async def execute(self, message, args) -> str:
        try:
            if not args:
                return "Usage: `!roast @username`"

            target_user = await self._parse_target_user(message)
            if not target_user:
                return "Could not find that user. Try mentioning them."

            if target_user.id == message.author.id:
                return (
                    "Nice try, but I'm not helping you roast yourself. That's just sad."
                )

            if target_user.bot or target_user.id == Config.BOT_USER_ID:
                return "I don't roast bots. We need to stick together."

            logger.info(
                f"Roast command invoked by {message.author.display_name} targeting {target_user.display_name}"
            )

            messages = await self._search_user_messages(message, target_user)

            if not messages:
                return f"{target_user.display_name} hasn't said anything interesting enough to roast."

            if len(messages) < 3:
                return f"I need more material to work with. {target_user.display_name} has barely said anything."

            roast = await self._generate_roast(target_user, messages)
            return roast

        except discord.Forbidden:
            logger.error("Permission denied when searching for messages")
            return "I don't have permission to search messages here."
        except Exception as e:
            logger.error(f"Error in RoastCommand: {e}")
            return "Something went wrong while trying to roast. Maybe that's karma."

    async def _parse_target_user(self, message):
        if message.mentions:
            for mentioned_user in message.mentions:
                if not mentioned_user.bot and mentioned_user.id != Config.BOT_USER_ID:
                    return mentioned_user
            if message.content.count("<@") >= 2:
                return message.mentions[0]
        return None

    async def _search_user_messages(self, message, target_user):
        try:
            search_context = message.guild if message.guild else message.channel

            messages = []
            async for msg in search_context.search(
                authors=[target_user], limit=MAX_MESSAGE_CONTEXT_FOR_AI
            ):
                if msg.author.id == target_user.id and msg.content.strip():
                    messages.append(msg)

            messages.sort(key=lambda m: m.created_at, reverse=True)
            return messages[:MAX_MESSAGE_CONTEXT_FOR_AI]

        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            return []

    async def _generate_roast(self, target_user, messages):
        try:
            if not self.ai_client.is_available():
                return (
                    "My AI is unavailable right now, but I'm sure "
                    f"{target_user.display_name} deserves a good roasting."
                )

            roast_prompt = self._get_roast_prompt(target_user)

            context_parts = [f"Messages from {target_user.display_name} to analyze:\n"]
            for msg in reversed(messages):
                context_parts.append(f"{target_user.display_name}: {msg.content}")

            context_parts.append(
                f"\nPlease generate a witty roast of {target_user.display_name} based on these messages."
            )
            formatted_context = "\n".join(context_parts)

            # logger.info(f"=== ROAST AI CONTEXT DEBUG ===")
            # logger.info(f"System Prompt:\n{roast_prompt}")
            # logger.info(f"User Context:\n{formatted_context}")
            # logger.info(f"Message count: {len(messages)}")
            # logger.info(f"Temperature: 1.2")
            # logger.info(f"=== END ROAST AI CONTEXT ===")

            ai_response = await self.ai_client._generate_with_config(
                formatted_context=formatted_context,
                system_prompt=roast_prompt,
                image_urls=None,
                enable_tools=False,
                temperature=1.2,
            )

            return (
                ai_response
                if ai_response
                else f"{target_user.display_name} is so boring even the AI couldn't think of a roast."
            )

        except Exception as e:
            logger.error(f"Error generating roast: {e}")
            return f"The AI crashed trying to process {target_user.display_name}'s messages. That says a lot."

    def _get_roast_prompt(self, target_user):
        try:
            if target_user.id == Config.DAN_USER_ID:
                prompt_file = (
                    "/home/tarquin/src/frank-the-chatter/prompts/roast_dan.txt"
                )
            else:
                prompt_file = "/home/tarquin/src/frank-the-chatter/prompts/roast.txt"

            with open(prompt_file) as f:
                prompt = f.read()
                return prompt.replace("{username}", target_user.display_name)
        except Exception as e:
            logger.error(f"Error loading roast prompt: {e}")
            return (
                "You are a witty AI roaster. Generate a clever, playful roast of "
                f"{target_user.display_name} based on their message history. "
                "Keep it fun and not genuinely mean."
            )
