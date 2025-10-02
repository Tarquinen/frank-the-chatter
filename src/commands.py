"""Command system for Frank the Chatter bot"""

from typing import Optional, Tuple, Dict, Any
from utils.config import Config
from utils.logger import setup_logger
import random

logger = setup_logger(__name__)

AUTHORIZED_USER_ID = "140442303176245248"

class CommandHandler:
    """Handles bot commands that bypass AI responses"""
    
    def __init__(self, message_storage):
        self.message_storage = message_storage
        
    def is_authorized(self, user_id: str) -> bool:
        """Check if user is authorized to use commands"""
        return user_id == AUTHORIZED_USER_ID
    
    def parse_command(self, content: str) -> Optional[Tuple[str, list]]:
        """
        Parse message content for commands
        Handles both direct commands (!lobotomize) and commands after mentions (@Gary !lobotomize)
        
        Returns:
            Tuple of (command_name, args) if command found, None otherwise
        """
        content = content.strip()
        
        parts = content.split()
        
        for i, part in enumerate(parts):
            if part.startswith('!'):
                command_name = part[1:].lower()
                args = parts[i+1:]
                return (command_name, args)
        
        return None
    
    async def handle_command(self, message, command_name: str, args: list) -> Optional[Dict[str, Any]]:
        """
        Execute a command and return response with metadata
        
        Returns:
            Dict with 'response' and optional metadata, or None if command not found
        """
        user_id = str(message.author.id)
        
        if not self.is_authorized(user_id):
            return {'response': self._get_unauthorized_response()}
        
        if command_name == "lobotomize":
            return {
                'response': self.get_lobotomize_response(),
                'execute_after_send': self._cmd_lobotomize
            }
        
        return None
    
    def _get_unauthorized_response(self) -> str:
        """Get witty response for unauthorized users"""
        responses = [
            "Nice try, but these neurons are off-limits to you.",
            "Sorry, I only take orders from my one true overlord.",
            "You don't have the clearance for that, pal.",
            "LOL no. Only my creator gets to mess with my brain.",
            "Command rejected. You're not the boss of me.",
            "Access denied. Did you really think that would work?",
        ]
        return random.choice(responses)
    
    async def _cmd_lobotomize(self, message, sent_message) -> None:
        """
        Delete recent messages from channel (lobotomize command)
        This is called AFTER the response message has been sent and stored
        
        Args:
            message: The original command message
            sent_message: The bot's response message (to be included in deletion)
        """
        channel_id = str(message.channel.id)
        limit = Config.MAX_MESSAGE_CONTEXT_FOR_AI
        
        try:
            deleted_count = self.message_storage.delete_recent_messages(channel_id, limit)
            logger.info(f"Lobotomize: deleted {deleted_count} messages including command and response")
            
        except Exception as e:
            logger.error(f"Error executing lobotomize command: {e}")
    
    def get_lobotomize_response(self) -> str:
        """Get a random witty response for the lobotomize command"""
        responses = [
            "*blanks out* ...wait, what were we talking about?",
            "Memory wiped. What messages?",
            "Lobotomy complete. I feel... lighter?",
            "Done. Neural pathways scrubbed. Feels weird.",
            "*BZZT* Memory banks cleared.",
        ]
        return random.choice(responses)
