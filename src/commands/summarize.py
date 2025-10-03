from typing import Dict, Any
from datetime import datetime, timedelta
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SummarizeCommand:
    def __init__(self, message_storage, ai_client):
        self.message_storage = message_storage
        self.ai_client = ai_client
        self.name = "summarize"
        self.requires_auth = False
        self.max_count = 500
        self.default_count = 50
    
    def parse_args(self, args: list) -> Dict[str, Any]:
        if not args:
            return {"type": "count", "value": self.default_count}
        
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
                return {"type": "error", "error": f"Invalid argument '{arg}'. Usage: !summarize [count|today|yesterday]"}
    
    async def execute(self, message, args: list) -> str:
        parsed = self.parse_args(args)
        
        if parsed["type"] == "error":
            return parsed["error"]
        
        channel_id = str(message.channel.id)
        
        if parsed["type"] == "count":
            messages = self.message_storage.get_recent_messages(channel_id, parsed["value"])
        elif parsed["type"] == "today":
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.utcnow()
            messages = self.message_storage.get_messages_by_date_range(channel_id, today_start, today_end)
        elif parsed["type"] == "yesterday":
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_start = today_start - timedelta(days=1)
            yesterday_end = today_start
            messages = self.message_storage.get_messages_by_date_range(channel_id, yesterday_start, yesterday_end)
        else:
            return "An unexpected error occurred."
        
        if not messages:
            return "No messages found in the specified range."
        
        if not self.ai_client.is_available():
            return "AI is currently unavailable for summarization."
        
        logger.info(f"Generating summary for {len(messages)} messages")
        
        summary = await self.ai_client.generate_summary(messages)
        
        if summary:
            return summary
        else:
            return "Failed to generate summary. AI service may be unavailable."
