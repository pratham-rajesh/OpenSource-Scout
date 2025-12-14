"""
Verify Migration
================
Checks if the new tables were created successfully.
"""

from app import app
from models import db, ChatSession, Conversation
import uuid

def verify():
    """Verify new tables exist and work."""
    with app.app_context():
        # Test creating a session
        test_session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=test_session_id,
            user_id=1,  # Assuming user with ID 1 exists
            total_messages=0
        )
        db.session.add(session)
        db.session.commit()
        print(f"✓ Created test ChatSession: {test_session_id[:8]}...")

        # Test creating a conversation message
        message = Conversation(
            session_id=test_session_id,
            user_id=1,
            role='user',
            content='Test message',
            message_metadata={'intent': 'test'},
            tokens_used=10
        )
        db.session.add(message)
        db.session.commit()
        print("✓ Created test Conversation message")

        # Query back
        retrieved_session = ChatSession.query.filter_by(session_id=test_session_id).first()
        print(f"✓ Retrieved session: {retrieved_session}")
        print(f"✓ Session has {len(retrieved_session.messages)} message(s)")

        # Cleanup
        db.session.delete(session)
        db.session.commit()
        print("✓ Cleanup completed")

        print("\n✅ All verification tests passed!")

if __name__ == '__main__':
    verify()
