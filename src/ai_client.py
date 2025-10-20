"""AI client for Frank the Chatter using Google Gemini API"""

import asyncio
from pathlib import Path
import re
import tempfile
from typing import Any

import aiohttp
import google.genai as genai
from google.genai import types

from utils.config import PROMPT_DIR, Config
from utils.constants import (
    AI_DEFAULT_TEMPERATURE,
    AI_MAX_IMAGE_UPLOAD,
    AI_MAX_RESPONSE_CHARS,
    AI_MAX_TOKENS,
    AI_RESPONSE_TRUNCATE_TO,
    AI_TOP_K,
    AI_TOP_P,
    MAX_MESSAGE_CONTEXT_FOR_AI,
)
from utils.logger import setup_logger

logger = setup_logger()


class AIClient:
    """Handles AI interactions with Google Gemini API"""

    def __init__(self):
        """Initialize the AI client with Gemini configuration"""
        self.client = None
        self.system_prompt = self._load_system_prompt()
        if Config.ENABLE_PERSONALITY_FEATURE:
            self.personality_prompt = self._load_system_prompt("personality.txt")
        else:
            self.personality_prompt = ""
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Gemini client"""
        try:
            if not Config.AI_API_KEY:
                logger.warning("GEMINI_API_KEY not found - AI responses will be disabled")
                return

            # Initialize Gemini client with API key
            self.client = genai.Client(api_key=Config.AI_API_KEY)
            logger.info(f"AI client initialized with model: {Config.AI_MODEL}")

        except Exception as e:
            logger.error(f"Failed to initialize AI client: {e}")
            self.client = None

    def _load_system_prompt(self, prompt_file: str = "conversation.txt") -> str:
        """Load a system prompt from prompts directory"""
        try:
            prompt_path = PROMPT_DIR / prompt_file
            if prompt_path.exists():
                return prompt_path.read_text().strip()
            else:
                logger.warning(f"{prompt_file} not found, using default system prompt")
                return "You are Frank, an AI in a Discord chat."
        except Exception as e:
            logger.error(f"Failed to load system prompt: {e}")
            return "You are Frank, an AI in a Discord chat."

    async def generate_response(
        self,
        context_messages: list[dict],
        mentioned_by: str,
        user_personality: dict[str, Any] | None = None,
    ) -> tuple[str | None, dict[str, Any] | None]:
        """
        Generate an AI response based on conversation context

        Args:
            context_messages: List of recent messages from database (including the mention)
            mentioned_by: Username who mentioned the bot
            user_personality: Optional personality data for the user

        Returns:
            Tuple of (response_text, personality_changes) or (None, None) if AI is unavailable
            personality_changes is a dict with 'updates' and 'deletions' lists or None
        """
        if not self.client:
            logger.warning("AI client not available - returning fallback response")
            return (
                f"Hi {mentioned_by}! My AI is currently unavailable, but I'm still logging our conversation.",
                None,
            )

        try:
            # Format conversation context for AI
            formatted_context, image_urls = self._format_context_for_ai(
                context_messages, mentioned_by, user_personality
            )

            # Generate response using Gemini
            response = await self._generate_conversation_response(formatted_context, image_urls)

            if response:
                clean_response, personality_changes = self._parse_personality_changes(response)
                logger.info(f"Generated AI response for {mentioned_by} ({len(clean_response)} characters)")
                return clean_response, personality_changes
            else:
                logger.warning("AI generated empty response")
                return (
                    f"Hi {mentioned_by}! I heard you mention me, but I'm not sure how to respond right now.",
                    None,
                )

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return f"Hi {mentioned_by}! I'm having some trouble with my AI right now, but I'm still here!", None

    def _format_context_for_ai(
        self, context_messages: list[dict], mentioned_by: str, user_personality: dict[str, Any] | None = None
    ):
        """Format conversation context for the AI model, extracting image URLs"""
        context_parts = []
        image_urls = []

        # Add recent conversation context
        if context_messages:
            context_parts.append("Recent conversation context:")
            for msg in context_messages[-MAX_MESSAGE_CONTEXT_FOR_AI:]:
                username = msg.get("username", "Unknown")
                content = msg.get("content", "")

                message_text = f"{username}: {content}" if content.strip() else f"{username}:"

                if msg.get("has_attachments") and msg.get("media_files"):
                    try:
                        attachments = msg["media_files"] if isinstance(msg["media_files"], list) else []
                        for att in attachments:
                            url = att.get("url", "")
                            content_type = att.get("content_type", "")
                            if url and content_type and content_type.startswith("image/"):
                                image_urls.append(url)
                                message_text += " [attached image]"
                    except Exception as e:
                        logger.warning(f"Failed to parse media_files: {e}")

                if content.strip() or msg.get("has_attachments"):
                    context_parts.append(message_text)

        # Add personality information if available and enabled
        if Config.ENABLE_PERSONALITY_FEATURE and user_personality:
            from personality_manager import PersonalityManager

            personality_mgr = PersonalityManager("")
            personality_text = personality_mgr.format_personality_for_prompt(user_personality)
            if personality_text:
                context_parts.append(personality_text)

        # Add instruction for response
        context_parts.append(f"\nPlease respond as Frank to {mentioned_by}.")

        formatted_context = "\n".join(context_parts)

        return formatted_context, image_urls

    async def _download_and_upload_image(self, url: str):
        """Download image from URL and upload to Gemini"""
        if not self.client:
            return None

        try:
            async with aiohttp.ClientSession() as session, session.get(url) as resp:
                if resp.status != 200:
                    logger.warning(f"Failed to download image from {url}: HTTP {resp.status}")
                    return None

                image_data = await resp.read()

                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                    tmp_file.write(image_data)
                    tmp_path = tmp_file.name

                loop = asyncio.get_event_loop()
                uploaded_file = await loop.run_in_executor(None, lambda: self.client.files.upload(file=tmp_path))

                Path(tmp_path).unlink()

                logger.info(f"Uploaded image to Gemini: {uploaded_file.name}")
                return uploaded_file

        except Exception as e:
            logger.error(f"Failed to download/upload image from {url}: {e}")
            return None

    async def _generate_with_config(
        self,
        formatted_context: str,
        system_prompt: str,
        image_urls: list[str] | None = None,
        enable_tools: bool = True,
        temperature: float = AI_DEFAULT_TEMPERATURE,
        max_tokens: int | None = None,
    ) -> str | None:
        """Generate response using Gemini API with configurable options and retry logic"""
        max_retries = 3
        initial_retry_delay = 2.0
        retry_delay = initial_retry_delay

        for attempt in range(max_retries):
            try:
                return await self._generate_with_config_impl(
                    formatted_context, system_prompt, image_urls, enable_tools, temperature, max_tokens
                )
            except Exception as e:
                error_str = str(e)
                error_type = type(e).__name__

                is_retryable = (
                    "503" in error_str
                    or "500" in error_str
                    or "429" in error_str
                    or "UNAVAILABLE" in error_str
                    or "RESOURCE_EXHAUSTED" in error_str
                    or "ResourceExhausted" in error_type
                    or "TooManyRequests" in error_type
                    or "ServerError" in error_type
                    or "DeadlineExceeded" in error_type
                    or "overloaded" in error_str.lower()
                )

                if is_retryable:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Gemini API temporary error (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {retry_delay:.1f}s..."
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        logger.error(f"Gemini API error after {max_retries} attempts: {e}")
                else:
                    logger.error(f"Gemini API non-retryable error: {e}", exc_info=True)
                    break

        return None

    async def _generate_with_config_impl(
        self,
        formatted_context: str,
        system_prompt: str,
        image_urls: list[str] | None = None,
        enable_tools: bool = True,
        temperature: float = AI_DEFAULT_TEMPERATURE,
        max_tokens: int | None = None,
    ) -> str | None:
        """Internal implementation of generate_with_config"""
        try:
            uploaded_files = []

            if image_urls and len(image_urls) > 0:
                logger.info(f"Processing {len(image_urls)} image(s) for AI request")
                for url in image_urls[-AI_MAX_IMAGE_UPLOAD:]:
                    uploaded_file = await self._download_and_upload_image(url)
                    if uploaded_file:
                        uploaded_files.append(uploaded_file)

            content_parts = [formatted_context, *uploaded_files] if uploaded_files else formatted_context

            config_kwargs = {
                "system_instruction": system_prompt,
                "max_output_tokens": max_tokens if max_tokens is not None else AI_MAX_TOKENS,
                "temperature": temperature,
                "top_p": AI_TOP_P,
                "top_k": AI_TOP_K,
                "safety_settings": [
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                ],
            }

            if enable_tools:
                config_kwargs["tools"] = [
                    types.Tool(google_search=types.GoogleSearch()),
                    types.Tool(code_execution=types.ToolCodeExecution()),
                ]

            config = types.GenerateContentConfig(**config_kwargs)

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self._sync_generate_content, content_parts, config)

            if self.client:
                for uploaded_file in uploaded_files:
                    try:
                        await loop.run_in_executor(
                            None,
                            lambda f=uploaded_file: self.client.files.delete(name=f.name),
                        )
                    except Exception as e:
                        logger.warning(f"Failed to delete uploaded file {uploaded_file.name}: {e}")

            if not response:
                logger.warning("Gemini API returned None response")
                return None

            try:
                text = response.text.strip() if response.text else ""
            except (AttributeError, ValueError) as e:
                logger.warning(f"Unable to access response.text: {e}")
                if hasattr(response, "candidates") and response.candidates:
                    candidate = response.candidates[0]
                    logger.warning(f"Finish reason: {candidate.finish_reason}")
                    if hasattr(candidate, "safety_ratings") and candidate.safety_ratings:
                        logger.warning(f"Safety ratings: {candidate.safety_ratings}")
                    if candidate.finish_reason == "SAFETY":
                        logger.error("Response blocked by safety filter")
                return None

            if not text:
                logger.warning("Gemini API returned empty text")
                if hasattr(response, "candidates") and response.candidates:
                    candidate = response.candidates[0]
                    logger.warning(f"Finish reason: {candidate.finish_reason}")
                    if hasattr(candidate, "safety_ratings") and candidate.safety_ratings:
                        logger.warning(f"Safety ratings: {candidate.safety_ratings}")
                else:
                    logger.warning(f"No candidates in response. Response type: {type(response)}")
                return None

            if len(text) > AI_MAX_RESPONSE_CHARS:
                logger.warning(f"Response too long ({len(text)} chars), truncating to {AI_MAX_RESPONSE_CHARS}")
                text = text[:AI_RESPONSE_TRUNCATE_TO] + "..."

            return text

        except Exception:
            raise

    async def _generate_conversation_response(
        self, formatted_context: str, image_urls: list[str] | None = None
    ) -> str | None:
        """Generate conversational response with tools and image support enabled"""
        combined_prompt = self.system_prompt
        if Config.ENABLE_PERSONALITY_FEATURE and self.personality_prompt:
            combined_prompt = f"{self.system_prompt}\n\n{self.personality_prompt}"

        return await self._generate_with_config(
            formatted_context=formatted_context,
            system_prompt=combined_prompt,
            image_urls=image_urls,
            enable_tools=True,
            temperature=1.0,
        )

    def _parse_personality_changes(self, response_text: str) -> tuple[str, dict[str, Any] | None]:
        """
        Extract personality updates and deletions from AI response

        Args:
            response_text: Full response from AI

        Returns:
            Tuple of (clean_response, dict with 'updates' and 'deletions' lists or None)
        """
        from datetime import datetime

        update_pattern = r"\[PERSONALITY_UPDATE\](.*?)\[/PERSONALITY_UPDATE\]"
        delete_pattern = r"\[PERSONALITY_DELETE\](.*?)\[/PERSONALITY_DELETE\]"

        update_matches = re.findall(update_pattern, response_text, re.DOTALL)
        delete_matches = re.findall(delete_pattern, response_text, re.DOTALL)

        personality_updates = []
        for match in update_matches:
            lines = match.strip().split("\n")
            update = {}
            for line in lines:
                line = line.strip()
                if line.startswith("- importance:"):
                    update["importance"] = line.split(":", 1)[1].strip()
                elif line.startswith("- content:"):
                    update["content"] = line.split(":", 1)[1].strip()
                elif line.startswith("- source:"):
                    update["source"] = line.split(":", 1)[1].strip()

            if "content" in update and "importance" in update:
                update["added_at"] = datetime.now().isoformat()
                if "source" not in update:
                    update["source"] = "Conversation context"
                personality_updates.append(update)

        personality_deletions = []
        for match in delete_matches:
            lines = match.strip().split("\n")
            deletion = {}
            for line in lines:
                line = line.strip()
                if line.startswith("- content:"):
                    deletion["content"] = line.split(":", 1)[1].strip()
                elif line.startswith("- reason:"):
                    deletion["reason"] = line.split(":", 1)[1].strip()

            if "content" in deletion:
                personality_deletions.append(deletion)

        clean_response = re.sub(update_pattern, "", response_text, flags=re.DOTALL)
        clean_response = re.sub(delete_pattern, "", clean_response, flags=re.DOTALL).strip()

        if personality_updates or personality_deletions:
            return clean_response, {
                "updates": personality_updates if personality_updates else [],
                "deletions": personality_deletions if personality_deletions else [],
            }

        return clean_response, None

    def _sync_generate_content(self, content, config: types.GenerateContentConfig):
        """Synchronous wrapper for Gemini API call"""
        if self.client:
            return self.client.models.generate_content(model=Config.AI_MODEL, contents=content, config=config)
        return None

    def is_available(self) -> bool:
        """Check if AI client is available and configured"""
        return self.client is not None

    async def generate_summary(self, messages: list[dict]) -> str | None:
        """
        Generate a conversation summary using summarize.txt prompt

        Args:
            messages: List of messages to summarize

        Returns:
            Summary text or None if AI unavailable
        """
        if not self.client:
            logger.warning("AI client not available for summarization")
            return None

        try:
            logger.info(f"Loading summarize prompt and formatting {len(messages)} messages")
            summarize_prompt = self._load_system_prompt("summarize.txt")

            context_parts = ["Conversation history to summarize:\n"]
            for msg in messages:
                timestamp = msg.get("timestamp", "")
                username = msg.get("username", "Unknown")
                content = msg.get("content", "")

                if timestamp:
                    try:
                        from datetime import datetime

                        dt = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
                        time_str = dt.strftime("%H:%M")
                    except Exception as te:
                        logger.debug(f"Failed to parse timestamp {timestamp}: {te}")
                        time_str = "??:??"
                else:
                    time_str = "??:??"

                message_line = f"[{time_str}] {username}: {content}"

                if msg.get("has_attachments"):
                    message_line += " [attached media]"

                context_parts.append(message_line)

            context_parts.append("\nPlease provide a summary of this conversation.")
            formatted_context = "\n".join(context_parts)

            logger.info(f"Formatted context length: {len(formatted_context)} characters")

            return await self._generate_with_config(
                formatted_context=formatted_context,
                system_prompt=summarize_prompt,
                image_urls=None,
                enable_tools=False,
                temperature=AI_DEFAULT_TEMPERATURE,
            )

        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            return None

    def get_model_info(self) -> dict:
        """Get information about the current AI model"""
        return {
            "model": Config.AI_MODEL,
            "available": self.is_available(),
            "max_tokens": AI_MAX_TOKENS,
            "api_configured": bool(Config.AI_API_KEY),
        }
