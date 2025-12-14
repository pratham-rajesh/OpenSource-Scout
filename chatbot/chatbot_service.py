"""
Production Chatbot Service
===========================
Main orchestration service integrating all components.
"""

import os
import re
from chatbot.conversation_manager import get_conversation_manager
from chatbot.intent_classifier import get_intent_classifier
from chatbot.tool_executor import get_tool_executor
from config.prompts import RESPONSE_GENERATION_PROMPT

# Try to import Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class ChatbotService:
    """
    Production-grade RAG chatbot service.

    Orchestrates:
    - Conversation management
    - Intent classification
    - Tool execution
    - Response generation
    - Basic security filtering
    """

    def __init__(self):
        """Initialize chatbot service with all components."""
        self.conversation_manager = get_conversation_manager()
        self.intent_classifier = get_intent_classifier()
        self.tool_executor = get_tool_executor()

        # Initialize LLM clients
        self.groq_client = None
        self.openai_client = None

        # Initialize Groq
        groq_key = os.getenv("GROQ_API_KEY")
        if GROQ_AVAILABLE and groq_key and groq_key != "your_groq_key_here":
            try:
                self.groq_client = Groq(api_key=groq_key)
                print("ChatbotService: Groq initialized")
            except Exception as e:
                print(f"ChatbotService: Groq init failed: {e}")

        # Initialize OpenAI as fallback
        openai_key = os.getenv("OPENAI_API_KEY")
        if OPENAI_AVAILABLE and openai_key and openai_key != "your_openai_key_here":
            try:
                self.openai_client = OpenAI(api_key=openai_key)
                print("ChatbotService: OpenAI initialized")
            except Exception as e:
                print(f"ChatbotService: OpenAI init failed: {e}")

    def get_chat_response(self, user_id, user_message, session_id=None):
        """
        Main orchestration method for chat responses.

        Parameters:
        - user_id: Current user ID
        - user_message: User's message
        - session_id: Optional session ID

        Returns:
        - dict with response, session_id, sources, intent
        """
        try:
            # 1. Input validation
            user_message = self._validate_input(user_message)

            # 2. Session management
            session = self.conversation_manager.get_or_create_session(user_id, session_id)
            conversation_history = self.conversation_manager.get_conversation_history(
                session.session_id, user_id, limit=10
            )

            # Convert to simple format for intent classifier
            history_for_intent = [
                {'role': msg.role, 'content': msg.content}
                for msg in conversation_history[-3:]  # Last 3 messages
            ]

            # 3. Intent classification
            intent_result = self.intent_classifier.classify_intent(
                user_message, history_for_intent
            )
            intent = intent_result['intent']
            entities = intent_result['entities']

            # 4. Tool execution
            tool_results = self.tool_executor.execute_tools(intent, entities, user_id)

            # 5. Build context for LLM
            tool_context = self.tool_executor.format_tool_results(intent, tool_results)

            # 6. Generate response
            response = self._generate_response(
                user_message, intent, tool_context, conversation_history
            )

            # 7. Security filtering
            filtered_response = self._filter_sensitive_data(response)

            # 8. Store conversation
            self.conversation_manager.add_message(
                session.session_id, user_id, 'user', user_message,
                metadata={'intent': intent, 'entities': entities}
            )

            self.conversation_manager.add_message(
                session.session_id, user_id, 'assistant', filtered_response,
                metadata={'tools_used': list(tool_results.keys())}
            )

            # 9. Extract sources
            sources = self._extract_sources(tool_results, intent)

            return {
                'response': filtered_response,
                'session_id': session.session_id,
                'sources': sources,
                'intent': intent
            }

        except Exception as e:
            print(f"ChatbotService error: {e}")
            return {
                'response': "Sorry, I encountered an error. Please try again.",
                'session_id': session_id,
                'sources': [],
                'intent': 'error'
            }

    def _validate_input(self, message):
        """Basic input validation."""
        if not message:
            raise ValueError("Empty message")

        # Limit length
        message = message[:2000]

        # Strip HTML tags (basic)
        message = re.sub(r'<[^>]+>', '', message)

        return message.strip()

    def _generate_response(self, user_message, intent, tool_context, conversation_history):
        """Generate response using LLM."""

        # Build conversation history for LLM
        messages = [{"role": "system", "content": RESPONSE_GENERATION_PROMPT}]

        # Add recent conversation history
        for msg in conversation_history[-4:]:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Add tool context and user message
        if tool_context:
            user_prompt = f"Context:\n{tool_context}\n\nUser: {user_message}"
        else:
            user_prompt = user_message

        messages.append({"role": "user", "content": user_prompt})

        # Try Groq first
        if self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.6,
                    max_tokens=400
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"Groq error: {e}")

        # Fallback to OpenAI
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"OpenAI error: {e}")

        # Ultimate fallback
        return self._fallback_response(intent, tool_context)

    def _fallback_response(self, intent, tool_context):
        """Fallback response when LLM unavailable."""
        if intent == 'search_issues':
            return f"Here are some issues I found:\n\n{tool_context}\n\n💡 Click on any issue to learn more!"
        elif intent == 'view_history':
            return f"Your contribution history:\n\n{tool_context}"
        elif intent == 'get_stats':
            return f"Your statistics:\n\n{tool_context}"
        else:
            return "I'm here to help! Try:\n• Find Python beginner issues\n• Show my stats\n• How am I doing?"

    def _filter_sensitive_data(self, response):
        """Basic security filtering."""
        # Remove API keys (basic patterns)
        patterns = {
            r'gsk_[a-zA-Z0-9]{52,}': '[GROQ_KEY_REDACTED]',
            r'sk-[a-zA-Z0-9]{48,}': '[API_KEY_REDACTED]',
            r'gh[pousr]_[a-zA-Z0-9]{36,}': '[GITHUB_TOKEN_REDACTED]',
        }

        for pattern, replacement in patterns.items():
            response = re.sub(pattern, replacement, response)

        return response

    def _extract_sources(self, tool_results, intent):
        """Extract source references from tool results."""
        sources = []

        if intent == 'search_issues':
            issues = tool_results.get('issues', [])
            for issue in issues[:3]:
                url = issue.get('issue_url') or issue.get('url')
                title = issue.get('issue_title') or issue.get('title', 'Issue')
                repo = issue.get('repo_name') or issue.get('repo', 'Repository')

                if url:
                    sources.append({
                        'title': title,
                        'url': url,
                        'repo': repo
                    })

        return sources

    def clear_session(self, user_id, session_id):
        """Clear a conversation session."""
        return self.conversation_manager.clear_session(session_id, user_id)


# Global chatbot service instance
_chatbot_service = None

def get_chatbot():
    """Get or create the global chatbot service."""
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
    return _chatbot_service
