"""Configuration management for Frank the Chatter bot"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Get project root directory
PROJECT_ROOT = Path.cwd()

# Load environment variables from project root
load_dotenv(PROJECT_ROOT / ".env")

# Prompt file paths
PROMPT_DIR = PROJECT_ROOT / "prompts"
CONVERSATION_PROMPT_PATH = PROMPT_DIR / "conversation.txt"
SUMMARIZE_PROMPT_PATH = PROMPT_DIR / "summarize.txt"


class Config:
    """Configuration settings for the bot"""

    # Discord Configuration
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    BOT_USER_ID = int(os.getenv("BOT_USER_ID", "0"))
    DAN_USER_ID = int(os.getenv("DAN_USER_ID", "0"))

    # AI API Configuration
    AI_API_KEY = os.getenv("GEMINI_API_KEY")
    AI_API_BASE_URL = os.getenv(
        "AI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1"
    )
    AI_MODEL = os.getenv("AI_MODEL", "gemini-2.5-flash")
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "2000"))

    # Storage Configuration (absolute paths from project root)
    DATABASE_PATH = os.getenv(
        "DATABASE_PATH", str(PROJECT_ROOT / "data" / "conversations.db")
    )
    LOG_FILE_PATH = os.getenv(
        "LOG_FILE_PATH", str(PROJECT_ROOT / "data" / "logs" / "bot.log")
    )

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required_vars = ["DISCORD_TOKEN"]
        missing = [var for var in required_vars if not getattr(cls, var)]

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        # Create directories if they don't exist
        Path(cls.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(cls.LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
