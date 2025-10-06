from datetime import UTC, datetime, timedelta
from typing import Any

from utils.constants import SUMMARIZE_MAX_COUNT
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SummarizeCommand:
    def __init__(self, message_storage, ai_client):
        self.message_storage = message_storage
        self.ai_client = ai_client
        self.name = "summarize"
        self.requires_auth = False
        self.max_count = SUMMARIZE_MAX_COUNT

    def parse_args(self, args: list) -> dict[str, Any]:
        if not args:
            return {"type": "today", "value": None}

        arg = args[0].lower()

        if arg == "today":
            return {"type": "today", "value": None}
        elif arg == "yesterday":
            return {"type": "yesterday", "value": None}
        else:
            try:
                count = int(arg)
                if count <= 0:
                    return {"type": "error", "error": "Please provide a valid positive number."}
                if count > self.max_count:
                    return {"type": "error", "error": f"Maximum {self.max_count} messages. You requested {count}."}
                return {"type": "count", "value": count}
            except ValueError:
                return {
                    "type": "error",
                    "error": (
                        f"Invalid argument '{arg}'. Usage: !summarize "
                        "[count|today|yesterday]"
                    ),
                }

    async def execute(self, message, args: list) -> str:
        try:
            parsed = self.parse_args(args)

            if parsed["type"] == "error":
                return parsed["error"]

            channel_id = str(message.channel.id)

            if parsed["type"] == "count":
                messages = self.message_storage.get_recent_messages(channel_id, parsed["value"])
            elif parsed["type"] == "today":
                now = datetime.now(UTC)
                start = now - timedelta(hours=24)
                messages = self.message_storage.get_messages_by_date_range(channel_id, start, now)
            elif parsed["type"] == "yesterday":
                now = datetime.now(UTC)
                yesterday_end = now - timedelta(hours=24)
                yesterday_start = now - timedelta(hours=48)
                messages = self.message_storage.get_messages_by_date_range(channel_id, yesterday_start, yesterday_end)
            else:
                return "An unexpected error occurred."

            if not messages:
                logger.warning(f"No messages found for summarize request (type: {parsed['type']})")
                return "No messages found in the specified range."

            if not self.ai_client.is_available():
                logger.warning("AI client not available for summarization")
                return "AI is currently unavailable for summarization."

            logger.info(f"Generating summary for {len(messages)} messages")

            summary = await self.ai_client.generate_summary(messages)

            if summary:
                logger.info(f"Summary generated successfully ({len(summary)} characters)")
                return summary
            else:
                logger.error("AI returned None for summary")
                return "Failed to generate summary. AI service may be unavailable."
        except Exception as e:
            logger.error(f"Error in summarize command: {e}", exc_info=True)
            return f"An error occurred while generating the summary: {e!s}"
