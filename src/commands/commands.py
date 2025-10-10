"""Commands command - List available bot commands"""

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
                "description": "Frank provides a thoughtful recap of the conversation",
                "permission": "everyone",
            },
            {
                "name": "!bh (be helpful)",
                "description": "Larry takes Frank's seat, and he just wants to help you",
                "permission": "everyone",
            },
            {
                "name": "!roast @user",
                "description": "Frank digs through someone's message history and serves up a custom roast",
                "permission": "everyone",
            },
            {
                "name": "!lobotomize [count|all]",
                "description": "Wipe Frank's memory clean (careful with this one)",
                "permission": "dan only",
            },
            {
                "name": "!random_reply",
                "description": "Manually trigger Frank to pick a random user and reply to their most interesting message",
                "permission": "dan only",
            },
        ]

        response_lines = []

        for cmd in commands_info:
            if cmd["permission"] == "dan only" and not is_authorized:
                continue

            response_lines.append(f"**{cmd['name']}**")
            response_lines.append(f"  • {cmd['description']}")
            response_lines.append("")

        return "\n".join(response_lines).strip()
