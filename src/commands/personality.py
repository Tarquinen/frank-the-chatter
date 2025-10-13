from utils.config import PROMPT_DIR, Config
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PersonalityCommand:
    def __init__(self, personality_manager, ai_client):
        self.name = "personality"
        self.requires_auth = False
        self.personality_manager = personality_manager
        self.ai_client = ai_client

    async def execute(self, message, args) -> str:
        try:
            target_user = await self._parse_target_user(message, args)
            if not target_user:
                target_user = message.author

            if target_user.bot and target_user.id != Config.BOT_USER_ID:
                return "Bots don't have personalities. They're just code."

            logger.info(f"Personality command invoked by {message.author.display_name} for {target_user.display_name}")

            personality = self.personality_manager.get_user_personality(str(target_user.id))

            if not personality or not personality.get("points"):
                if target_user.id == message.author.id:
                    return "I don't know anything about your personality yet. Keep chatting with me!"
                else:
                    return f"I don't know anything about {target_user.display_name}'s personality yet."

            response = await self._generate_personality_response(target_user, personality)
            return response

        except Exception as e:
            logger.error(f"Error in PersonalityCommand: {e}")
            return "Something went wrong while checking the personality data."

    async def _parse_target_user(self, message, args):
        if message.mentions:
            for mentioned_user in message.mentions:
                if mentioned_user.id != Config.BOT_USER_ID:
                    return mentioned_user
        return None

    async def _generate_personality_response(self, target_user, personality):
        if not self.ai_client.is_available():
            formatted_points = self.personality_manager.format_personality_for_prompt(personality)
            return f"My AI is unavailable, but here's what I know about {target_user.display_name}:{formatted_points}"

        personality_prompt = self._get_personality_prompt()

        points = personality["points"]
        context_parts = [
            f"User to analyze: {target_user.display_name}\n",
            f"Personality points ({len(points)}/10):\n",
        ]

        for i, point in enumerate(points, 1):
            importance = point.get("importance", "unknown")
            content = point.get("content", "")
            context_parts.append(f"{i}. [{importance}] {content}")

        formatted_context = "\n".join(context_parts)

        ai_response = await self.ai_client._generate_with_config(
            formatted_context=formatted_context,
            system_prompt=personality_prompt,
            image_urls=None,
            enable_tools=False,
            temperature=0.8,
        )

        return (
            ai_response
            if ai_response
            else f"I have data on {target_user.display_name}, but I can't seem to summarize it right now."
        )

    def _get_personality_prompt(self):
        prompt_path = PROMPT_DIR / "personality_command.txt"
        return prompt_path.read_text().strip()
