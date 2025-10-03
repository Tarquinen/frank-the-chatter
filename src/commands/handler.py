"""Command system for Frank the Chatter bot"""

from typing import Optional, Tuple, Dict, Any
from utils.logger import setup_logger
import random

from .lobotomize import LobotomizeCommand
from .commands import CommandsCommand

logger = setup_logger(__name__)

AUTHORIZED_USER_ID = "140442303176245248"


class CommandHandler:
    """Handles bot commands that bypass AI responses"""

    def __init__(self, message_storage):
        self.message_storage = message_storage
        self.commands = {
            "lobotomize": LobotomizeCommand(message_storage),
            "commands": CommandsCommand(),
        }

    def is_authorized(self, user_id: str) -> bool:
        """Check if user is authorized to use commands"""
        return user_id == AUTHORIZED_USER_ID

    def parse_command(self, content: str) -> Optional[Tuple[str, list]]:
        """
        Parse message content for commands
        Handles both direct commands (!lobotomize) and commands after mentions (@Gary !lobotomize)

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

    async def handle_command(
        self, message, command_name: str, args: list
    ) -> Optional[Dict[str, Any]]:
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

        if command_name == "lobotomize":
            parsed = command.parse_args(args)
            if "error" in parsed:
                return {"response": parsed["error"]}

            delete_all = parsed["delete_all"]
            limit = parsed["limit"]

            return {
                "response": command.get_processing_response(delete_all),
                "execute_after_send": lambda msg, sent_msg: command.execute(
                    msg, sent_msg, limit, delete_all
                ),
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
