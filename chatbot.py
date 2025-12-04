"""
RAG Chatbot Service
===================
Provides contextual coding advice by querying solved issues from ChromaDB
and combining with user skill history to generate helpful responses.

Features:
- Query similar solved issues based on user questions
- Combine with user's skill profile for personalized advice
- Support for both OpenAI and Groq LLMs
- Fallback responses when AI is unavailable
"""

import os
from openai import OpenAI
from rag_engine import get_rag_engine
from models import UserSkill, SolvedIssue

# Try to import Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class ChatbotService:
    """
    RAG-powered chatbot for coding assistance.

    Uses ChromaDB to retrieve relevant solved issues and combines
    with user history to provide contextual debugging help.
    """

    def __init__(self):
        """Initialize chatbot with available LLM providers."""
        self.openai_client = None
        self.groq_client = None
        self.rag_engine = get_rag_engine()

        # Initialize OpenAI if available and not placeholder
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "your_openai_key_here":
            try:
                self.openai_client = OpenAI(api_key=openai_key)
            except Exception as e:
                print(f"OpenAI initialization failed: {e}")
                self.openai_client = None

        # Initialize Groq if available
        groq_key = os.getenv("GROQ_API_KEY")
        if GROQ_AVAILABLE and groq_key and groq_key != "your_groq_key_here":
            try:
                self.groq_client = Groq(api_key=groq_key)
                print("Groq client initialized successfully")
            except Exception as e:
                print(f"Groq initialization failed: {e}")
                self.groq_client = None

    def get_chat_response(self, user_id, user_message, conversation_history=None):
        """
        Generate chatbot response based on user question.

        Parameters:
        - user_id: Current user ID
        - user_message: User's question/message
        - conversation_history: Previous messages (optional)

        Returns:
        - dict with 'response', 'similar_issues', and 'sources'
        """
        # Get user context
        user_context = self._build_user_context(user_id)

        # Find similar solved issues from user's history
        similar_issues = self.rag_engine.find_similar_issues(
            user_id=user_id,
            query_text=user_message,
            n_results=3
        )

        # Get user's solved issues for additional context
        solved_issues = SolvedIssue.query.filter_by(user_id=user_id)\
            .order_by(SolvedIssue.solved_at.desc()).limit(5).all()

        # Build context from similar issues
        issues_context = self._format_similar_issues(similar_issues, solved_issues)

        # Generate LLM response
        llm_response = self._generate_llm_response(
            user_message=user_message,
            user_context=user_context,
            issues_context=issues_context,
            conversation_history=conversation_history
        )

        return {
            'response': llm_response,
            'similar_issues': similar_issues,
            'sources': self._extract_sources(solved_issues[:3])
        }

    def _build_user_context(self, user_id):
        """Build context about user's skills and experience."""
        skills = UserSkill.query.filter_by(user_id=user_id).all()
        patterns = self.rag_engine.get_user_patterns(user_id)

        context = []

        if skills:
            skill_text = ", ".join([
                f"{s.language} (Level {s.skill_level}, {s.issues_solved} solved)"
                for s in skills
            ])
            context.append(f"Your skills: {skill_text}")

        if patterns:
            context.append(f"You've solved {patterns['total_solved']} issues")
            if patterns['avg_difficulty'] > 0:
                context.append(f"Average difficulty tackled: {patterns['avg_difficulty']}/5")

        return "\n".join(context) if context else "You're just getting started!"

    def _format_similar_issues(self, similar_issues, solved_issues):
        """Format similar issues for LLM context."""
        if not similar_issues and not solved_issues:
            return "No previous similar issues found."

        formatted = []

        if similar_issues:
            formatted.append("Similar issues you've worked on:")
            for i, issue_text in enumerate(similar_issues, 1):
                formatted.append(f"{i}. {issue_text[:200]}...")

        return "\n".join(formatted)

    def _extract_sources(self, solved_issues):
        """Extract source references from solved issues."""
        sources = []
        for issue in solved_issues:
            sources.append({
                'title': issue.issue_title,
                'url': issue.issue_url,
                'repo': issue.repo_name,
                'language': issue.language
            })
        return sources

    def _generate_llm_response(self, user_message, user_context, issues_context, conversation_history=None):
        """Generate response using available LLM."""
        # Build system prompt
        system_prompt = """You are a helpful coding assistant for open source contributors.

FORMATTING RULES (CRITICAL):
- ALWAYS use bullet points (•) or numbered lists (1., 2., 3.)
- NEVER write long paragraphs
- Keep each point to ONE line maximum
- Maximum 3-5 bullet points per response
- Use line breaks between points
- Be EXTREMELY concise

CONTENT RULES:
- Give only actionable advice
- Reference user's skills when relevant
- No theory, only practical steps

Example format:
• First actionable tip
• Second specific step
• Third concrete suggestion"""

        # Build user prompt
        user_prompt = f"""User Profile:
{user_context}

{issues_context}

User Question: {user_message}

Please provide helpful coding advice based on their experience and history."""

        # Try Groq first (faster and often free)
        if self.groq_client:
            try:
                messages = [{"role": "system", "content": system_prompt}]

                # Add conversation history if provided
                if conversation_history:
                    messages.extend(conversation_history[-4:])  # Last 4 messages for context

                messages.append({"role": "user", "content": user_prompt})

                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",  # Current recommended model
                    messages=messages,
                    temperature=0.6,
                    max_tokens=300
                )

                return response.choices[0].message.content.strip()

            except Exception as e:
                print(f"Groq error: {e}")

        # Fallback to OpenAI
        if self.openai_client:
            try:
                messages = [{"role": "system", "content": system_prompt}]

                if conversation_history:
                    messages.extend(conversation_history[-4:])

                messages.append({"role": "user", "content": user_prompt})

                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )

                return response.choices[0].message.content.strip()

            except Exception as e:
                print(f"OpenAI error: {e}")

        # Ultimate fallback - rule-based response
        return self._fallback_response(user_message, user_context)

    def _fallback_response(self, user_message, user_context):
        """Generate fallback response when AI is unavailable."""
        message_lower = user_message.lower()

        # Pattern matching for common questions
        if any(word in message_lower for word in ['debug', 'error', 'bug', 'fix']):
            return f"""Based on your profile:\n{user_context}\n\nFor debugging:
1. Check the error message carefully - it often points to the exact issue
2. Use console.log() or print() to trace variable values
3. Review similar issues you've solved before
4. Search the repository's existing issues for similar problems
5. Don't hesitate to ask for help in the issue comments!"""

        elif any(word in message_lower for word in ['start', 'begin', 'first', 'new']):
            return f"""Great to see you getting started!\n{user_context}\n\nTips for your first contribution:
1. Read the CONTRIBUTING.md file carefully
2. Set up the development environment locally
3. Start with issues labeled 'good-first-issue'
4. Make small, focused changes
5. Write clear commit messages and PR descriptions"""

        elif any(word in message_lower for word in ['test', 'testing']):
            return f"""Testing advice:\n{user_context}\n\nBest practices:
1. Run existing tests first: npm test or python -m pytest
2. Write tests for your changes
3. Test edge cases and error conditions
4. Check test coverage
5. Make sure all tests pass before submitting PR"""

        else:
            return f"""I'm here to help with your open source contributions!\n{user_context}\n\nI can help you with:
- Debugging similar problems you've encountered
- Understanding codebases in languages you know
- Best practices for contributing
- Getting unstuck on issues

Ask me specific questions about coding problems, or use the quick action buttons below!"""

    def get_quick_actions(self, user_id):
        """Generate contextual quick action buttons based on user profile."""
        skills = UserSkill.query.filter_by(user_id=user_id).all()
        patterns = self.rag_engine.get_user_patterns(user_id)

        actions = []

        # Default actions
        actions.append({
            'label': '💡 How do I start?',
            'message': 'How do I get started with my first contribution?'
        })

        if skills:
            top_skill = max(skills, key=lambda s: s.issues_solved)
            actions.append({
                'label': f'🐛 Debug {top_skill.language}',
                'message': f'I\'m stuck on a {top_skill.language} issue. How should I debug it?'
            })

        actions.append({
            'label': '📝 Writing good PRs',
            'message': 'What makes a good pull request?'
        })

        if patterns and patterns['total_solved'] > 0:
            actions.append({
                'label': '📊 My progress',
                'message': 'Show me my contribution patterns and progress'
            })
        else:
            actions.append({
                'label': '🎯 Best practices',
                'message': 'What are best practices for open source contributions?'
            })

        return actions


# Global chatbot instance
_chatbot_service = None

def get_chatbot():
    """Get or create the global chatbot service."""
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
    return _chatbot_service
