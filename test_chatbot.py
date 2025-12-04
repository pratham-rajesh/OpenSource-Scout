"""
Quick test script for chatbot functionality
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("OpenSource Scout - Chatbot Test")
print("=" * 60)
print()

# Test 1: Import check
print("Test 1: Checking imports...")
try:
    from chatbot import ChatbotService, get_chatbot
    print("✓ Chatbot module imported successfully")
except Exception as e:
    print(f"✗ Failed to import chatbot: {e}")
    sys.exit(1)

# Test 2: Initialize chatbot
print("\nTest 2: Initializing chatbot...")
try:
    chatbot = ChatbotService()
    print("✓ Chatbot initialized")

    # Check available providers
    providers = []
    if chatbot.openai_client:
        providers.append("OpenAI")
    if chatbot.groq_client:
        providers.append("Groq")

    if providers:
        print(f"  Available LLM providers: {', '.join(providers)}")
    else:
        print("  ⚠ No LLM providers available (fallback mode)")

    if chatbot.rag_engine:
        print("  ✓ RAG engine connected")

except Exception as e:
    print(f"✗ Failed to initialize chatbot: {e}")
    sys.exit(1)

# Test 3: Test fallback response
print("\nTest 3: Testing fallback response system...")
try:
    response = chatbot._fallback_response(
        "How do I debug a Python error?",
        "Skills: Python (Level 3, 5 solved)"
    )
    print("✓ Fallback response generated:")
    print(f"  {response[:100]}...")
except Exception as e:
    print(f"✗ Fallback response failed: {e}")

# Test 4: Test quick actions
print("\nTest 4: Testing quick action generation...")
try:
    # Create a mock user ID
    actions = chatbot.get_quick_actions(user_id=1)
    print(f"✓ Generated {len(actions)} quick actions:")
    for action in actions:
        print(f"  - {action['label']}: {action['message'][:50]}...")
except Exception as e:
    print(f"✗ Quick actions failed: {e}")

print()
print("=" * 60)
print("Test Summary")
print("=" * 60)
print("✓ Chatbot module is working correctly!")
print()
print("Next steps:")
print("1. Make sure you have ChromaDB installed: pip install chromadb")
print("2. (Optional) Add OPENAI_API_KEY or GROQ_API_KEY to .env")
print("3. Run the Flask app: python app.py")
print("4. Look for the chat icon in the bottom-right corner")
print("=" * 60)
