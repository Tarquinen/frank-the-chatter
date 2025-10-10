#!/usr/bin/env python3
"""Diagnostic script to test Gemini API responses in group chat context"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / "src"))

import google.genai as genai
from google.genai import types

from database import MessageDatabase
from utils.config import Config


def test_with_actual_context():
    """Test API with actual group chat context from database"""
    print("=== Gemini API Diagnostics ===\n")

    if not Config.AI_API_KEY:
        print("ERROR: No GEMINI_API_KEY found")
        return

    client = genai.Client(api_key=Config.AI_API_KEY)

    # Get actual group chat context
    db = MessageDatabase()

    # Get most active channel (group chat)
    channels = db.get_channels_with_messages()
    if not channels:
        print("No messages in database")
        return

    group_channel_id = channels[0]["channel_id"]
    print(f"Testing with channel: {group_channel_id}")
    print(f"Messages in channel: {channels[0]['message_count']}\n")

    # Get recent messages from that channel
    recent = db.get_recent_messages(group_channel_id, 25)
    print(f"Retrieved {len(recent)} messages for context\n")

    # Format context like the bot does
    context_parts = []
    if recent:
        context_parts.append("Recent conversation context:")
        for msg in recent[-10:]:  # Last 10 messages
            username = msg.get("username", "Unknown")
            content = msg.get("content", "")
            if content.strip():
                context_parts.append(f"{username}: {content}")

    context_parts.append("\ntarquin_dan just mentioned you with: @frank what's up?")
    context_parts.append("\nPlease respond as Frank to tarquin_dan.")

    formatted_context = "\n".join(context_parts)

    print("Context length:", len(formatted_context), "chars\n")
    print("--- CONTEXT START ---")
    print(formatted_context[:500], "..." if len(formatted_context) > 500 else "")
    print("--- CONTEXT END ---\n")

    # Load system prompt
    prompt_path = Path(__file__).parent / "config" / "prompt.txt"
    system_prompt = prompt_path.read_text().strip() if prompt_path.exists() else "You are Frank"

    print(f"System prompt length: {len(system_prompt)} chars\n")

    # Test with tools (current config)
    config_with_tools = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=min(Config.AI_MAX_TOKENS, 500),
        temperature=1,
        top_p=0.95,
        top_k=20,
        tools=[
            types.Tool(google_search=types.GoogleSearch()),
            types.Tool(code_execution=types.ToolCodeExecution()),
            types.Tool(url_context=types.UrlContext()),
        ],
    )

    print("=== Test 1: With Tools (Current Config) ===")
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model=Config.AI_MODEL, contents=formatted_context, config=config_with_tools
            )

            # Try to access text
            try:
                text = response.text if hasattr(response, "text") else None
                if text:
                    print(f"Attempt {attempt+1}: SUCCESS - {len(text)} chars")
                else:
                    print(f"Attempt {attempt+1}: EMPTY - No text")
                    if hasattr(response, "candidates") and response.candidates:
                        candidate = response.candidates[0]
                        print(f"  Finish reason: {candidate.finish_reason}")
                        if hasattr(candidate, "safety_ratings"):
                            print(f"  Safety ratings: {candidate.safety_ratings}")
            except Exception as e:
                print(f"Attempt {attempt+1}: ERROR accessing text - {e}")
                if hasattr(response, "candidates") and response.candidates:
                    candidate = response.candidates[0]
                    print(f"  Finish reason: {candidate.finish_reason}")

        except Exception as e:
            print(f"Attempt {attempt+1}: API ERROR - {e}")

    print("\n=== Test 2: Without Tools ===")
    config_no_tools = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=min(Config.AI_MAX_TOKENS, 500),
        temperature=1,
        top_p=0.95,
        top_k=20,
    )

    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model=Config.AI_MODEL, contents=formatted_context, config=config_no_tools
            )

            try:
                text = response.text if hasattr(response, "text") else None
                if text:
                    print(f"Attempt {attempt+1}: SUCCESS - {len(text)} chars")
                    print(f"  Preview: {text[:100]}")
                else:
                    print(f"Attempt {attempt+1}: EMPTY")
            except Exception as e:
                print(f"Attempt {attempt+1}: ERROR - {e}")

        except Exception as e:
            print(f"Attempt {attempt+1}: API ERROR - {e}")


if __name__ == "__main__":
    test_with_actual_context()
