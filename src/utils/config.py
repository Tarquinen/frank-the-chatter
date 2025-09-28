"""Configuration management for Frank the Chatter bot"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from parent directory
load_dotenv(".env")

class Config:
    """Configuration settings for the bot"""
    
    # Discord Configuration
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    BOT_USER_ID = os.getenv("BOT_USER_ID")
    
    # AI API Configuration  
    AI_API_KEY = os.getenv("GEMINI_API_KEY")  # Using Gemini from .env
    AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1")
    AI_MODEL = os.getenv("AI_MODEL", "gemini-2.5-flash")
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "20000"))
    
    # Storage Configuration
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/conversations.db")
    MEDIA_STORAGE_PATH = os.getenv("MEDIA_STORAGE_PATH", "./data/media")
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "./data/logs/bot.log")
    
    # Performance Settings
    MAX_ACTIVE_CONVERSATIONS = int(os.getenv("MAX_ACTIVE_CONVERSATIONS", "100"))
    MAX_MESSAGES_PER_CONVERSATION = int(os.getenv("MAX_MESSAGES_PER_CONVERSATION", "1000"))
    MAX_MESSAGE_CONTEXT_FOR_AI = int(os.getenv("MAX_MESSAGE_CONTEXT_FOR_AI", "100"))
    MAX_MEDIA_FILE_SIZE_MB = int(os.getenv("MAX_MEDIA_FILE_SIZE_MB", "50"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required_vars = ["DISCORD_TOKEN"]
        missing = [var for var in required_vars if not getattr(cls, var)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        # Create directories if they don't exist
        Path(cls.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(cls.MEDIA_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
        Path(cls.LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
