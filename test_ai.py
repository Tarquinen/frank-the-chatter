#!/usr/bin/env python3
"""Test script to verify AI integration works"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from ai_client import AIClient
from utils.logger import setup_logger

logger = setup_logger()

async def test_ai_response():
    """Test AI response generation"""
    print("🧪 Testing Frank's AI Integration...")
    
    # Initialize AI client
    ai_client = AIClient()
    
    # Check if AI is available
    model_info = ai_client.get_model_info()
    print(f"📊 Model Info: {model_info}")
    
    if not ai_client.is_available():
        print("❌ AI client not available - check your GEMINI_API_KEY in .env")
        return
    
    # Test AI response with mock context
    mock_messages = [
        {"username": "alice", "content": "Hey everyone!"},
        {"username": "bob", "content": "How's everyone doing today?"},
        {"username": "charlie", "content": "Pretty good, just working on some code"},
        {"username": "tarquin_dan", "content": "@frank what do you think about this conversation?"}
    ]
    
    print("\n💬 Testing AI response generation...")
    response = await ai_client.generate_response(
        context_messages=mock_messages,
        user_message="@frank what do you think about this conversation?",
        mentioned_by="tarquin_dan"
    )
    
    if response:
        print(f"✅ AI Response Generated ({len(response)} chars):")
        print(f"🤖 Frank: {response}")
    else:
        print("❌ No response generated")

if __name__ == "__main__":
    asyncio.run(test_ai_response())