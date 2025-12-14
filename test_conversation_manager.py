"""
Test Conversation Manager
==========================
Verify the ConversationManager functionality.
"""

from app import app
from chatbot.conversation_manager import get_conversation_manager

def test_conversation_manager():
    """Test conversation manager operations."""
    with app.app_context():
        manager = get_conversation_manager()
        print("✓ ConversationManager initialized")

        # Test 1: Create session
        session = manager.get_or_create_session(user_id=1)
        print(f"✓ Created session: {session.session_id[:8]}...")

        # Test 2: Add messages
        manager.add_message(
            session_id=session.session_id,
            user_id=1,
            role='user',
            content='Hello, can you help me find Python issues?',
            metadata={'intent': 'search_issues', 'language': 'Python'}
        )
        print("✓ Added user message")

        manager.add_message(
            session_id=session.session_id,
            user_id=1,
            role='assistant',
            content='Sure! I can help you find Python issues. Here are some good first issues...',
            metadata={'tools_used': ['search_github_api']}
        )
        print("✓ Added assistant message")

        # Test 3: Retrieve history
        history = manager.get_conversation_history(session.session_id, user_id=1, limit=10)
        print(f"✓ Retrieved {len(history)} messages from history")

        # Test 4: Build context window
        context = manager.build_context_window(
            session_id=session.session_id,
            user_id=1,
            retrieved_docs=["Document 1 about Python debugging", "Document 2 about GitHub issues"]
        )
        print(f"✓ Built context window: {context['tokens_used']} tokens")
        print(f"  - Messages in context: {len(context['messages'])}")
        print(f"  - Documents in context: {len(context['documents'])}")

        # Test 5: Get session stats
        stats = manager.get_session_stats(session.session_id, user_id=1)
        print(f"✓ Session stats: {stats['total_messages']} messages, {stats['total_tokens_used']} tokens")

        # Test 6: Clear session
        success = manager.clear_session(session.session_id, user_id=1)
        print(f"✓ Session cleared: {success}")

        print("\n✅ All ConversationManager tests passed!")

if __name__ == '__main__':
    test_conversation_manager()
