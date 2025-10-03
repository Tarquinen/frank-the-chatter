"""Commands command - List available bot commands"""

from typing import Dict, Any
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CommandsCommand:
    """Handles the !commands command"""

    def __init__(self):
        self.name = "commands"
        self.requires_auth = False

    def get_response(self, is_authorized: bool) -> str:
        """
        Get formatted list of available commands

        Args:
            is_authorized: Whether the user is authorized (Dan)

        Returns:
            Formatted string listing all commands
        """
        commands_info = [
            {
                "name": "!summarize [count|today|yesterday]",
                "description": "Generate AI summary of conversation history",
                "permission": "anyone",
            },
            {
                "name": "!bh (be helpful)",
                "description": "Switch to helpful mode (no personality, just useful assistance)",
                "permission": "anyone",
            },
            {
                "name": "!lobotomize [count|all]",
                "description": "Delete messages from bot's memory",
                "permission": "dan only",
            },
        ]

        response_lines = ["**Available Commands:**\n"]

        for cmd in commands_info:
            if cmd["permission"] == "dan only" and not is_authorized:
                continue

            response_lines.append(f"**{cmd['name']}**")
            response_lines.append(f"  • {cmd['description']}")
            response_lines.append(f"  • Permission: {cmd['permission']}")
            response_lines.append("")

        return "\n".join(response_lines).strip()
