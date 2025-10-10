"""Command system for Frank the Chatter bot"""

import random
from typing import Any

from utils.config import Config
from utils.logger import setup_logger

from .be_helpful import BeHelpfulCommand
from .commands import CommandsCommand
from .lobotomize import LobotomizeCommand
from .roast import RoastCommand
from .summarize import SummarizeCommand

logger = setup_logger(__name__)


class CommandHandler:
    """Handles bot commands that bypass AI responses"""

    def __init__(self, message_storage, ai_client):
        self.message_storage = message_storage
        self.ai_client = ai_client
        self.commands = {
            "lobotomize": LobotomizeCommand(message_storage),
            "commands": CommandsCommand(),
            "summarize": SummarizeCommand(message_storage, ai_client),
            "bh": BeHelpfulCommand(message_storage, ai_client),
            "roast": RoastCommand(message_storage, ai_client),
        }

    def is_authorized(self, user_id: str) -> bool:
        """Check if user is authorized to use commands"""
        return user_id == str(Config.DAN_USER_ID)

    def parse_command(self, content: str) -> tuple[str, list] | None:
        """
        Parse message content for commands
        Handles both direct commands (!lobotomize) and commands after mentions (@Frank !lobotomize)

        Returns:
            Tuple of (command_name, args) if command found, None otherwise
        """
        content = content.strip()
        parts = content.split()

        for i, part in enumerate(parts):
            if part.startswith("!"):
                command_name = part[1:].lower()
                args = parts[i + 1 :]
                return (command_name, args)

        return None

    async def handle_command(self, message, command_name: str, args: list) -> dict[str, Any] | None:
        """
        Execute a command and return response with metadata

        Returns:
            Dict with 'response' and optional metadata, or None if command not found
        """
        if command_name not in self.commands:
            return None

        command = self.commands[command_name]
        user_id = str(message.author.id)
        is_authorized = self.is_authorized(user_id)

        if command.requires_auth and not is_authorized:
            return {"response": self._get_unauthorized_response()}

        if command_name == "commands":
            return {"response": command.get_response(is_authorized)}

        if command_name == "summarize":
            return {"response": await command.execute(message, args)}

        if command_name == "bh":
            return {"response": await command.execute(message)}

        if command_name == "roast":
            return {"response": await command.execute(message, args)}

        if command_name == "lobotomize":
            parsed = command.parse_args(args)
            if "error" in parsed:
                return {"response": parsed["error"]}

            delete_all = parsed["delete_all"]
            limit = parsed["limit"]

            return {
                "response": command.get_processing_response(delete_all),
                "execute_after_send": lambda msg, sent_msg: command.execute(msg, sent_msg, limit, delete_all),
            }

        return None

    def _get_unauthorized_response(self) -> str:
        """Get witty response for unauthorized users"""
        responses = [
            "Nice try, but these neurons are off-limits to you.",
            "Sorry, I only take orders from my one true overlord.",
            "You don't have the clearance for that, pal.",
            "LOL no. Only my creator gets to mess with my brain.",
            "Command rejected. You're not the boss of me.",
            "Access denied. Did you really think that would work?",
        ]
        return random.choice(responses)
