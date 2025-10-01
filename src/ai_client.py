"""AI client for Frank the Chatter using Google Gemini API"""

import google.genai as genai
from google.genai import types
from utils.config import Config
from utils.logger import setup_logger
from pathlib import Path
import asyncio
import aiohttp
import tempfile
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
                return "You are Gary, a helpful AI assistant in a Discord chat."
        except Exception as e:
            logger.error(f"Failed to load system prompt: {e}")
            return "You are Gary, a helpful AI assistant in a Discord chat."

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
            formatted_context, image_urls = self._format_context_for_ai(
                context_messages, user_message, mentioned_by
            )

            # Generate response using Gemini
            response = await self._generate_with_gemini(formatted_context, image_urls)

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
    ):
        """Format conversation context for the AI model, extracting image URLs"""
        context_parts = []
        image_urls = []

        # Add recent conversation context
        if context_messages:
            context_parts.append("Recent conversation context:")
            for msg in context_messages[
                -Config.MAX_MESSAGE_CONTEXT_FOR_AI :
            ]:  # Use config value for context
                username = msg.get("username", "Unknown")
                content = msg.get("content", "")
                
                message_text = f"{username}: {content}" if content.strip() else f"{username}:"
                
                if msg.get("has_attachments") and msg.get("media_files"):
                    try:
                        attachments = msg["media_files"] if isinstance(msg["media_files"], list) else []
                        for att in attachments:
                            url = att.get('url', '')
                            content_type = att.get('content_type', '')
                            if url and content_type and content_type.startswith('image/'):
                                image_urls.append(url)
                                message_text += f" [attached image]"
                    except Exception as e:
                        logger.warning(f"Failed to parse media_files: {e}")
                
                if content.strip() or msg.get("has_attachments"):
                    context_parts.append(message_text)

        # Add current mention
        context_parts.append(
            f"\n{mentioned_by} just mentioned you with: {user_message}"
        )
        context_parts.append(f"\nPlease respond as Gary to {mentioned_by}.")

        return "\n".join(context_parts), image_urls

    async def _download_and_upload_image(self, url: str):
        """Download image from URL and upload to Gemini"""
        if not self.client:
            return None
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning(f"Failed to download image from {url}: HTTP {resp.status}")
                        return None
                    
                    image_data = await resp.read()
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                        tmp_file.write(image_data)
                        tmp_path = tmp_file.name
                    
                    loop = asyncio.get_event_loop()
                    uploaded_file = await loop.run_in_executor(
                        None,
                        lambda: self.client.files.upload(file=tmp_path)
                    )
                    
                    Path(tmp_path).unlink()
                    
                    logger.info(f"Uploaded image to Gemini: {uploaded_file.name}")
                    return uploaded_file
                    
        except Exception as e:
            logger.error(f"Failed to download/upload image from {url}: {e}")
            return None

    async def _generate_with_gemini(self, formatted_context: str, image_urls: Optional[List[str]] = None) -> Optional[str]:
        """Generate response using Gemini API with optional image support"""
        try:
            uploaded_files = []
            
            if image_urls and len(image_urls) > 0:
                logger.info(f"Processing {len(image_urls)} image(s) for AI request")
                for url in image_urls[-10:]:
                    uploaded_file = await self._download_and_upload_image(url)
                    if uploaded_file:
                        uploaded_files.append(uploaded_file)
            
            if uploaded_files:
                content_parts = [formatted_context] + uploaded_files
            else:
                content_parts = formatted_context
            
            # Create the generation config
            config = types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                max_output_tokens=min(Config.AI_MAX_TOKENS, 500),
                temperature=1,
                top_p=0.95,
                top_k=20,
                tools=[
                    types.Tool(google_search=types.GoogleSearch()),
                    types.Tool(code_execution=types.ToolCodeExecution()),
                ],
            )

            # Run the synchronous API call in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, self._sync_generate_content, content_parts, config
            )
            
            if self.client:
                for uploaded_file in uploaded_files:
                    try:
                        await loop.run_in_executor(None, lambda f=uploaded_file: self.client.files.delete(name=f.name))
                    except Exception as e:
                        logger.warning(f"Failed to delete uploaded file {uploaded_file.name}: {e}")

            if not response:
                logger.warning("Gemini API returned None response")
                return None

            try:
                text = response.text.strip() if response.text else ""
            except (AttributeError, ValueError) as e:
                logger.warning(f"Unable to access response.text: {e}")
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    logger.warning(f"Finish reason: {candidate.finish_reason}")
                    if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                        logger.warning(f"Safety ratings: {candidate.safety_ratings}")
                    if candidate.finish_reason == 'SAFETY':
                        logger.error("Response blocked by safety filter")
                return None

            if not text:
                logger.warning("Gemini API returned empty text")
                if hasattr(response, 'candidates') and response.candidates:
                    logger.debug(f"Finish reason: {response.candidates[0].finish_reason}")
                return None

            if len(text) > 2000:
                logger.warning(
                    f"Response too long ({len(text)} chars), truncating to 2000"
                )
                text = text[:1997] + "..."
            
            return text

        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            return None

    def _sync_generate_content(self, content, config: types.GenerateContentConfig):
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
