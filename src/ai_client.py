"""AI client for Frank the Chatter using Google Gemini API"""

import google.genai as genai
from google.genai import types
from utils.config import Config
from utils.logger import setup_logger
from pathlib import Path
import asyncio
from typing import List, Optional

logger = setup_logger()


class AIClient:
    """Handles AI interactions with Google Gemini API"""

    def __init__(self):
        """Initialize the AI client with Gemini configuration"""
        self.client = None
        self.system_prompt = self._load_system_prompt()
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Gemini client"""
        try:
            if not Config.AI_API_KEY:
                logger.warning(
                    "GEMINI_API_KEY not found - AI responses will be disabled"
                )
                return

            # Initialize Gemini client with API key
            self.client = genai.Client(api_key=Config.AI_API_KEY)
            logger.info(f"AI client initialized with model: {Config.AI_MODEL}")

        except Exception as e:
            logger.error(f"Failed to initialize AI client: {e}")
            self.client = None

    def _load_system_prompt(self) -> str:
        """Load the system prompt from config file"""
        try:
            prompt_path = Path(__file__).parent.parent / "config" / "prompt.txt"
            if prompt_path.exists():
                return prompt_path.read_text().strip()
            else:
                logger.warning("prompt.txt not found, using default system prompt")
                return "You are Frank, a helpful AI assistant in a Discord chat."
        except Exception as e:
            logger.error(f"Failed to load system prompt: {e}")
            return "You are Frank, a helpful AI assistant in a Discord chat."

    async def generate_response(
        self, context_messages: List[dict], user_message: str, mentioned_by: str
    ) -> Optional[str]:
        """
        Generate an AI response based on conversation context

        Args:
            context_messages: List of recent messages from database
            user_message: The message that mentioned the bot
            mentioned_by: Username who mentioned the bot

        Returns:
            Generated response text or None if AI is unavailable
        """
        if not self.client:
            logger.warning("AI client not available - returning fallback response")
            return f"Hi {mentioned_by}! My AI is currently unavailable, but I'm still logging our conversation."

        try:
            # Format conversation context for AI
            formatted_context = self._format_context_for_ai(
                context_messages, user_message, mentioned_by
            )

            # Generate response using Gemini
            response = await self._generate_with_gemini(formatted_context)

            if response:
                logger.info(
                    f"Generated AI response for {mentioned_by} ({len(response)} characters)"
                )
                return response
            else:
                logger.warning("AI generated empty response")
                return f"Hi {mentioned_by}! I heard you mention me, but I'm not sure how to respond right now."

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return f"Hi {mentioned_by}! I'm having some trouble with my AI right now, but I'm still here!"

    def _format_context_for_ai(
        self, context_messages: List[dict], user_message: str, mentioned_by: str
    ) -> str:
        """Format conversation context for the AI model"""
        context_parts = []

        # Add recent conversation context
        if context_messages:
            context_parts.append("Recent conversation context:")
            for msg in context_messages[
                -Config.MAX_MESSAGE_CONTEXT_FOR_AI :
            ]:  # Use config value for context
                username = msg.get("username", "Unknown")
                content = msg.get("content", "")
                if content.strip():  # Only include non-empty messages
                    context_parts.append(f"{username}: {content}")

        # Add current mention
        context_parts.append(
            f"\n{mentioned_by} just mentioned you with: {user_message}"
        )
        context_parts.append(f"\nPlease respond as Gary to {mentioned_by}.")

        return "\n".join(context_parts)

    async def _generate_with_gemini(self, formatted_context: str) -> Optional[str]:
        """Generate response using Gemini API"""
        try:
            # Create the generation config
            config = types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                max_output_tokens=min(
                    Config.AI_MAX_TOKENS, 2000
                ),  # Keep Discord responses reasonable
                temperature=1,  # Balanced creativity
                top_p=0.95,
                top_k=20,
            )

            # Run the synchronous API call in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, self._sync_generate_content, formatted_context, config
            )

            if response and response.text:
                return response.text.strip()
            else:
                logger.warning("Gemini API returned empty response")
                return None

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None

    def _sync_generate_content(self, content: str, config: types.GenerateContentConfig):
        """Synchronous wrapper for Gemini API call"""
        if self.client:
            return self.client.models.generate_content(
                model=Config.AI_MODEL, contents=content, config=config
            )
        return None

    def is_available(self) -> bool:
        """Check if AI client is available and configured"""
        return self.client is not None

    def get_model_info(self) -> dict:
        """Get information about the current AI model"""
        return {
            "model": Config.AI_MODEL,
            "available": self.is_available(),
            "max_tokens": Config.AI_MAX_TOKENS,
            "api_configured": bool(Config.AI_API_KEY),
        }
