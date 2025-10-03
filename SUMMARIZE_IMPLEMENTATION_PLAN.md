# Implementation Plan for `!summarize` Command

## Overview
Add a new `!summarize` command that allows users to generate AI-powered summaries of Discord conversation history using the existing `prompts/summarize.txt` prompt.

## Command Specification

### Usage
```
!summarize              # Summarize last 50 messages (default)
!summarize 100          # Summarize last 100 messages
!summarize today        # Summarize all messages from today
!summarize yesterday    # Summarize all messages from yesterday
```

### Requirements
- **Auth**: Not required (anyone can use)
- **Prompt**: Uses `prompts/summarize.txt`
- **AI Model**: Same Gemini model as conversation mode

## Architecture

### 1. New Command Class: `src/commands/summarize.py`

```python
class SummarizeCommand:
    def __init__(self, message_storage, ai_client):
        self.message_storage = message_storage
        self.ai_client = ai_client
        self.name = "summarize"
        self.requires_auth = False
    
    def parse_args(self, args: list) -> Dict[str, Any]:
        # Returns: {"type": "count"|"today"|"yesterday", "value": int|None}
        pass
    
    async def execute(self, message, args: list) -> str:
        # Main execution logic
        pass
```

### 2. Database Enhancement: `src/database.py`

Add new method:
```python
def get_messages_by_date_range(self, channel_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """Get messages within a specific date range"""
    pass
```

### 3. AI Client Enhancement: `src/ai_client.py`

Add new method:
```python
async def generate_summary(self, messages: List[dict]) -> Optional[str]:
    """
    Generate a conversation summary using summarize.txt prompt
    
    Args:
        messages: List of messages to summarize
    
    Returns:
        Summary text or None if AI unavailable
    """
    pass
```

This method will:
- Load `prompts/summarize.txt` as system instruction
- Format messages for summarization context
- Call Gemini API with summary-specific configuration
- Return summary text

### 4. Command Handler Integration: `src/commands/handler.py`

Modifications needed:
```python
# 1. Import the new command
from .summarize import SummarizeCommand

# 2. Modify __init__ to accept ai_client
def __init__(self, message_storage, ai_client):
    self.message_storage = message_storage
    self.ai_client = ai_client
    self.commands = {
        "lobotomize": LobotomizeCommand(message_storage),
        "commands": CommandsCommand(),
        "summarize": SummarizeCommand(message_storage, ai_client),
    }

# 3. Add handler in handle_command() method
if command_name == "summarize":
    return {"response": await command.execute(message, args)}
```

### 5. Bot Integration: `src/bot.py`

Modify CommandHandler instantiation:
```python
# Change from:
self.command_handler = CommandHandler(self.message_storage)

# To:
self.command_handler = CommandHandler(self.message_storage, self.ai_client)
```

### 6. Update Commands List: `src/commands/commands.py`

Add to `commands_info` list:
```python
{
    "name": "!summarize",
    "description": "Generate AI summary of conversation history",
    "usage": "!summarize [count|today|yesterday]",
    "permission": "anyone",
}
```

## Implementation Details

### Argument Parsing Logic

1. **No args**: Default to last 50 messages
2. **Numeric arg**: Parse as message count
   - Validate: positive integer
   - Max limit: 500 messages (configurable)
3. **"today"**: Calculate date range from midnight to now (UTC)
4. **"yesterday"**: Calculate date range for previous day (UTC)
5. **Invalid arg**: Return error message with usage instructions

### Date Range Calculation

```python
from datetime import datetime, timedelta

# Today: midnight to now
today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
today_end = datetime.utcnow()

# Yesterday: previous day midnight to midnight
yesterday_start = today_start - timedelta(days=1)
yesterday_end = today_start
```

### Message Context Formatting

Format messages for summary context:
```
Conversation history to summarize:

[HH:MM] username: message content
[HH:MM] username: message content
...

Please provide a summary of this conversation.
```

### Error Handling

- **No messages found**: "No messages found in the specified range."
- **AI unavailable**: "AI is currently unavailable for summarization."
- **Invalid count**: "Please provide a valid positive number."
- **Too many messages**: "Maximum 500 messages. You requested {count}."

## File Changes Summary

### New Files
- `src/commands/summarize.py`
- `SUMMARIZE_IMPLEMENTATION_PLAN.md` (this file)

### Modified Files
- `src/commands/handler.py` - Add summarize command
- `src/commands/commands.py` - Add to commands list
- `src/database.py` - Add date range query method
- `src/ai_client.py` - Add generate_summary method
- `src/bot.py` - Pass ai_client to CommandHandler

## Configuration

No new config values needed. Uses existing:
- `Config.MAX_MESSAGE_CONTEXT_FOR_AI` as default limit
- `Config.AI_MODEL` for Gemini model
- `Config.AI_API_KEY` for API access

## Future Enhancements

Potential additions (not in scope):
- Date range: `!summarize 2025-01-01 2025-01-31`
- User filter: `!summarize @username`
- Topic focus: `!summarize 100 about python`
- Export summaries to file
- Scheduled automatic summaries
