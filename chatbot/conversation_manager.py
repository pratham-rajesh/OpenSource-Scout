"""
Conversation Manager
====================
Manages chat sessions and conversation history.

Features:
- Create and retrieve chat sessions
- Store and retrieve conversation messages
- Build context windows with token budgeting
- Auto-summarize long conversations
- Session cleanup
"""

import uuid
from datetime import datetime
from models import db, ChatSession, Conversation

# Try to import tiktoken for token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("tiktoken not installed. Using approximate token counting.")


class ConversationManager:
    """
    Manages conversation sessions and message history.

    Handles session lifecycle, message storage, and context window management
    with token budgeting for optimal LLM performance.
    """

    def __init__(self, max_context_tokens=6000):
        """
        Initialize conversation manager.

        Parameters:
        - max_context_tokens: Maximum tokens for context window (default: 6000)
        """
        self.max_context_tokens = max_context_tokens

        # Initialize token encoder if available
        if TIKTOKEN_AVAILABLE:
            try:
                self.encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
            except Exception as e:
                print(f"Failed to initialize tiktoken: {e}")
                self.encoder = None
        else:
            self.encoder = None

    def count_tokens(self, text):
        """
        Count tokens in text.

        Uses tiktoken if available, otherwise approximates (4 chars ≈ 1 token).
        """
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except:
                pass

        # Fallback: approximate token count
        return len(text) // 4

    def get_or_create_session(self, user_id, session_id=None):
        """
        Get existing session or create new one.

        Parameters:
        - user_id: Current user ID
        - session_id: Optional session ID (creates new if None)

        Returns:
        - ChatSession object
        """
        if session_id:
            # Try to find existing session
            session = ChatSession.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).first()

            if session:
                # Update last_active timestamp
                session.last_active = datetime.utcnow()
                db.session.commit()
                return session

        # Create new session
        new_session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=new_session_id,
            user_id=user_id,
            total_messages=0,
            total_tokens_used=0
        )

        db.session.add(session)
        db.session.commit()

        return session

    def get_conversation_history(self, session_id, user_id, limit=10):
        """
        Get conversation history for a session.

        Parameters:
        - session_id: Session ID
        - user_id: User ID (for security)
        - limit: Maximum number of messages to retrieve

        Returns:
        - List of Conversation objects (most recent first)
        """
        messages = Conversation.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).order_by(Conversation.created_at.desc()).limit(limit).all()

        # Reverse to get chronological order
        return list(reversed(messages))

    def add_message(self, session_id, user_id, role, content, metadata=None, tokens=None):
        """
        Add a message to the conversation.

        Parameters:
        - session_id: Session ID
        - user_id: User ID
        - role: 'user' or 'assistant'
        - content: Message content
        - metadata: Optional metadata dict (intent, tools_used, sources, etc.)
        - tokens: Optional token count (auto-calculated if None)

        Returns:
        - Conversation object
        """
        # Calculate tokens if not provided
        if tokens is None:
            tokens = self.count_tokens(content)

        # Create message
        message = Conversation(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            message_metadata=metadata or {},
            tokens_used=tokens
        )

        db.session.add(message)

        # Update session stats
        session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()

        if session:
            session.total_messages += 1
            session.total_tokens_used += tokens
            session.last_active = datetime.utcnow()

            # Auto-summarize if messages exceed threshold
            if session.total_messages >= 20 and session.total_messages % 10 == 0:
                # Mark for summarization (actual summarization happens in chatbot_service)
                if not session.summary:
                    session.summary = "[To be summarized]"

        db.session.commit()

        return message

    def build_context_window(self, session_id, user_id, retrieved_docs=None, max_tokens=None):
        """
        Build context window from conversation history and retrieved documents.

        Manages token budget:
        - Reserve tokens for conversation history
        - Reserve tokens for retrieved documents
        - Truncate oldest messages if over budget

        Parameters:
        - session_id: Session ID
        - user_id: User ID
        - retrieved_docs: List of retrieved document strings
        - max_tokens: Override default max_context_tokens

        Returns:
        - dict with 'messages' and 'documents' arrays
        """
        max_tokens = max_tokens or self.max_context_tokens
        retrieved_docs = retrieved_docs or []

        # Get conversation history (up to last 20 messages)
        messages = self.get_conversation_history(session_id, user_id, limit=20)

        # Calculate document tokens
        doc_tokens = sum(self.count_tokens(doc) for doc in retrieved_docs)

        # Reserve tokens: 60% for history, 40% for docs
        history_budget = int(max_tokens * 0.6)
        doc_budget = int(max_tokens * 0.4)

        # Truncate documents if needed
        if doc_tokens > doc_budget:
            truncated_docs = []
            current_tokens = 0
            for doc in retrieved_docs:
                doc_token_count = self.count_tokens(doc)
                if current_tokens + doc_token_count <= doc_budget:
                    truncated_docs.append(doc)
                    current_tokens += doc_token_count
                else:
                    break
            retrieved_docs = truncated_docs

        # Build message context (prioritize recent messages)
        context_messages = []
        current_tokens = 0

        # Add messages in reverse (newest first) until budget is reached
        for message in reversed(messages):
            message_tokens = message.tokens_used or self.count_tokens(message.content)

            if current_tokens + message_tokens <= history_budget:
                context_messages.insert(0, {
                    'role': message.role,
                    'content': message.content
                })
                current_tokens += message_tokens
            else:
                break

        return {
            'messages': context_messages,
            'documents': retrieved_docs,
            'tokens_used': current_tokens + sum(self.count_tokens(doc) for doc in retrieved_docs)
        }

    def summarize_session(self, session_id, user_id, llm_client=None):
        """
        Generate summary of conversation session.

        Uses LLM to create 2-3 sentence summary of the conversation.
        This summary can be used for long conversations to maintain context.

        Parameters:
        - session_id: Session ID
        - user_id: User ID
        - llm_client: LLM client (Groq or OpenAI)

        Returns:
        - Summary string or None if failed
        """
        if not llm_client:
            return None

        # Get all messages
        messages = self.get_conversation_history(session_id, user_id, limit=50)

        if not messages:
            return None

        # Build conversation text
        conversation_text = "\n".join([
            f"{msg.role.upper()}: {msg.content}"
            for msg in messages
        ])

        # Truncate if too long
        if len(conversation_text) > 4000:
            conversation_text = conversation_text[:4000] + "..."

        try:
            # Generate summary using LLM
            response = llm_client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Use Groq's fast model
                messages=[
                    {
                        "role": "system",
                        "content": "Summarize the following conversation in 2-3 concise sentences. Focus on the main topics discussed and any key decisions or outcomes."
                    },
                    {
                        "role": "user",
                        "content": conversation_text
                    }
                ],
                temperature=0.3,
                max_tokens=150
            )

            summary = response.choices[0].message.content.strip()

            # Update session
            session = ChatSession.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).first()

            if session:
                session.summary = summary
                db.session.commit()

            return summary

        except Exception as e:
            print(f"Error generating summary: {e}")
            return None

    def clear_session(self, session_id, user_id):
        """
        Clear all messages in a session.

        Parameters:
        - session_id: Session ID
        - user_id: User ID (for security)

        Returns:
        - True if successful, False otherwise
        """
        try:
            # Delete all messages
            Conversation.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).delete()

            # Delete session
            ChatSession.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).delete()

            db.session.commit()
            return True

        except Exception as e:
            print(f"Error clearing session: {e}")
            db.session.rollback()
            return False

    def get_session_stats(self, session_id, user_id):
        """
        Get statistics for a session.

        Returns:
        - dict with session stats or None if not found
        """
        session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()

        if not session:
            return None

        return {
            'session_id': session.session_id,
            'total_messages': session.total_messages,
            'total_tokens_used': session.total_tokens_used,
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'last_active': session.last_active.isoformat() if session.last_active else None,
            'summary': session.summary
        }


# Global conversation manager instance
_conversation_manager = None

def get_conversation_manager():
    """Get or create the global conversation manager."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
