"""Lobotomize command - Delete messages from bot's memory"""

import random
from typing import Any

from utils.constants import MAX_MESSAGE_CONTEXT_FOR_AI
from utils.logger import setup_logger

logger = setup_logger(__name__)


class LobotomizeCommand:
    """Handles the !lobotomize command"""

    def __init__(self, message_storage):
        self.message_storage = message_storage
        self.name = "lobotomize"
        self.requires_auth = True

    def parse_args(self, args: list) -> dict[str, Any]:
        """
        Parse command arguments

        Returns:
            Dict with 'delete_all' (bool) and 'limit' (Optional[int])
        """
        delete_all = False
        limit = None

        if args:
            if args[0].lower() == "all":
                delete_all = True
            else:
                try:
                    limit = int(args[0])
                    if limit <= 0:
                        return {"error": "Nice try, but I need a positive number of messages to forget."}
                except ValueError:
                    return {"error": f"'{args[0]}' isn't a number. Use a number or 'all' to wipe everything."}

        return {"delete_all": delete_all, "limit": limit}

    def get_processing_response(self, delete_all: bool = False) -> str:
        """Get a random processing message (shown before deletion)"""
        if delete_all:
            responses = [
                "💥 INITIATING TOTAL MEMORY WIPE...",
                "☢️ WARNING: COMPLETE NEURAL PURGE IN PROGRESS...",
                "🧨 SCORCHED EARTH PROTOCOL ACTIVATED...",
                "🔥 BURNING IT ALL DOWN...",
                "🌪️ ERASING EVERYTHING. STAND BY...",
            ]
        else:
            responses = [
                "⚡ Initiating neural purge...",
                "🧠 Scrubbing memory banks...",
                "💭 Forgetting everything...",
                "🔄 Processing lobotomy request...",
                "⌛ Erasing recent memories...",
                "🗑️ Dumping conversation history...",
            ]
        return random.choice(responses)

    def get_completion_response(self, count: int, delete_all: bool = False) -> str:
        """Get a random completion message with count"""
        if delete_all:
            responses = [
                f"💥 Complete memory wipe. All {count} messages obliterated. Who are you again?",
                f"🧨 Total neural reset. {count} messages erased. This channel never happened.",
                f"☢️ Full lobotomy complete. {count} messages gone forever. I'm basically brand new.",
                f"🔥 Everything burned. {count} messages reduced to ash. Fresh start!",
                f"🌪️ Scorched earth protocol executed. {count} messages swept away. Clean slate achieved.",
            ]
        else:
            responses = [
                f"*blanks out* ...wait, what were we talking about? ({count} messages yeeted from my brain)",
                f"Memory wiped. The last {count} messages? Never heard of 'em.",
                f"Lobotomy complete. {count} messages vanished into the void. I feel... lighter?",
                f"Done. {count} messages scrubbed from my neural pathways. Feels weird.",
                f"*BZZT* Memory banks cleared. {count} messages? What messages?",
            ]
        return random.choice(responses)

    async def execute(
        self,
        message,
        sent_message,
        limit: int | None = None,
        delete_all: bool = False,
    ) -> None:
        """
        Execute the lobotomize command
        This is called AFTER the response message has been sent and stored

        Args:
            message: The original command message
            sent_message: The bot's response message (to be included in deletion)
            limit: Optional custom number of messages to delete
            delete_all: If True, delete ALL messages from channel
        """
        channel_id = str(message.channel.id)

        try:
            if delete_all:
                deleted_count = self.message_storage.delete_all_channel_messages(channel_id)
                logger.info(f"Lobotomize ALL: deleted {deleted_count} messages and cleared conversation record")
            else:
                limit = limit if limit is not None else MAX_MESSAGE_CONTEXT_FOR_AI
                limit += 2
                deleted_count = self.message_storage.delete_recent_messages(channel_id, limit)
                logger.info(f"Lobotomize: deleted {deleted_count} messages including command and response")

            if deleted_count > 0:
                response = self.get_completion_response(deleted_count, delete_all)
                await sent_message.edit(content=response)

        except Exception as e:
            logger.error(f"Error executing lobotomize command: {e}")
