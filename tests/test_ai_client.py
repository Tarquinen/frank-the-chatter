import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_client import AIClient
from utils.logger import setup_logger
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = setup_logger()


class AIClientTester:
    def __init__(self):
        self.client = AIClient()
        self.logs = []
        
    def log_data(self, label, data):
        entry = f"\n{'='*80}\n{label}\n{'='*80}\n{data}\n"
        self.logs.append(entry)
        print(entry)
    
    async def test_generate_response(self):
        context_messages = [
            {
                "username": "Alice",
                "content": "Hey everyone!",
                "has_attachments": False,
            },
            {
                "username": "Bob",
                "content": "What's up?",
                "has_attachments": False,
            },
            {
                "username": "Charlie",
                "content": "@Gary can you help me with something?",
                "has_attachments": False,
            },
        ]
        
        user_message = "@Gary can you help me with something?"
        mentioned_by = "Charlie"
        
        self.log_data("SYSTEM PROMPT", self.client.system_prompt)
        self.log_data("MODEL INFO", str(self.client.get_model_info()))
        self.log_data("CONTEXT MESSAGES", str(context_messages))
        self.log_data("USER MESSAGE", user_message)
        self.log_data("MENTIONED BY", mentioned_by)
        
        formatted_context, image_urls = self.client._format_context_for_ai(
            context_messages, user_message, mentioned_by
        )
        
        self.log_data("FORMATTED CONTEXT SENT TO AI", formatted_context)
        self.log_data("IMAGE URLS", str(image_urls))
        
        print("\nGenerating AI response...")
        response = await self.client.generate_response(
            context_messages, user_message, mentioned_by
        )
        
        self.log_data("AI RESPONSE", response or "None")
        
        print(f"\n{'='*80}")
        print("TEST COMPLETE")
        print(f"{'='*80}")
        
        return response


async def main():
    print("Starting AI Client Test")
    print("="*80)
    
    tester = AIClientTester()
    
    if not tester.client.is_available():
        print("WARNING: AI client is not available (API key not configured)")
    
    await tester.test_generate_response()


if __name__ == "__main__":
    asyncio.run(main())
