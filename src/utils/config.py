"""Configuration management for Frank the Chatter bot"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Get project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Load environment variables from project root
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    """Configuration settings for the bot"""

    # Discord Configuration
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

    # AI API Configuration
    AI_API_KEY = os.getenv("GEMINI_API_KEY")  # Using Gemini from .env
    AI_API_BASE_URL = os.getenv(
        "AI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1"
    )
    AI_MODEL = os.getenv(
        "AI_MODEL", "gemini-2.5-flash"
    )  # Updated to use Gemini 2.5 Flash
    AI_MAX_TOKENS = int(
        os.getenv("AI_MAX_TOKENS", "2000")
    )  # Reduced for Discord responses

    # Storage Configuration (absolute paths from project root)
    DATABASE_PATH = os.getenv(
        "DATABASE_PATH", str(PROJECT_ROOT / "data" / "conversations.db")
    )
    LOG_FILE_PATH = os.getenv(
        "LOG_FILE_PATH", str(PROJECT_ROOT / "data" / "logs" / "bot.log")
    )

    # Performance Settings
    MAX_MESSAGE_CONTEXT_FOR_AI = int(os.getenv("MAX_MESSAGE_CONTEXT_FOR_AI", "100"))

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
