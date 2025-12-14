"""
Intent Classifier
=================
Classifies user messages into intents and extracts relevant entities.

Intents:
- search_issues: Find new GitHub issues to work on
- view_history: View past solved issues
- get_stats: Get user statistics/progress
- get_advice: Get coding advice or debugging help
- general_question: General programming questions
"""

import os
import json
import re
from config.prompts import INTENT_CLASSIFICATION_PROMPT

# Try to import Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("Groq not installed. Intent classification will use fallback mode.")


class IntentClassifier:
    """
    Classifies user intents and extracts entities using LLM.

    Uses Groq LLM for fast, accurate intent classification with entity extraction.
    Falls back to keyword-based classification if LLM is unavailable.
    """

    def __init__(self):
        """Initialize intent classifier with Groq client."""
        self.groq_client = None

        # Initialize Groq if available
        groq_key = os.getenv("GROQ_API_KEY")
        if GROQ_AVAILABLE and groq_key and groq_key != "your_groq_key_here":
            try:
                self.groq_client = Groq(api_key=groq_key)
                print("Intent Classifier: Groq client initialized")
            except Exception as e:
                print(f"Intent Classifier: Groq initialization failed: {e}")
                self.groq_client = None

    def classify_intent(self, user_message, conversation_history=None):
        """
        Classify user message intent and extract entities.

        Parameters:
        - user_message: User's message text
        - conversation_history: Optional list of previous messages for context

        Returns:
        - dict with 'intent', 'confidence', and 'entities'
        """
        # Try LLM-based classification first
        if self.groq_client:
            result = self._classify_with_llm(user_message, conversation_history)
            if result:
                return result

        # Fallback to keyword-based classification
        return self._classify_with_keywords(user_message)

    def _classify_with_llm(self, user_message, conversation_history=None):
        """
        Use Groq LLM for intent classification.

        Returns dict or None if failed.
        """
        try:
            # Build context from conversation history
            context = ""
            if conversation_history:
                recent_messages = conversation_history[-3:]  # Last 3 messages
                context = "\n".join([
                    f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}"
                    for msg in recent_messages
                ])
                context = f"\nRecent conversation:\n{context}\n\n"

            # Create prompt
            prompt = f"{INTENT_CLASSIFICATION_PROMPT}\n\n{context}User message: {user_message}"

            # Call Groq
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an intent classifier. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent classification
                max_tokens=200
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON from response
            # Try to extract JSON if wrapped in markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result_text = json_match.group()

            result = json.loads(result_text)

            # Validate result structure
            if 'intent' in result and 'confidence' in result:
                # Ensure entities dict exists
                if 'entities' not in result:
                    result['entities'] = {}

                # Validate intent is one of the allowed types
                valid_intents = ['search_issues', 'view_history', 'get_stats', 'get_advice', 'general_question']
                if result['intent'] not in valid_intents:
                    result['intent'] = 'general_question'
                    result['confidence'] = 0.5

                return result

        except Exception as e:
            print(f"LLM intent classification error: {e}")

        return None

    def _classify_with_keywords(self, user_message):
        """
        Fallback keyword-based intent classification.

        Uses simple keyword matching when LLM is unavailable.
        """
        message_lower = user_message.lower()

        # Search issues keywords
        search_keywords = [
            'find', 'search', 'show me issues', 'get issues', 'recommend', 'suggest',
            'looking for', 'need issues', 'want to work on', 'beginner issues'
        ]

        # View history keywords
        history_keywords = [
            'my history', 'what have i solved', 'show my', 'my solved', 'my past',
            'previously solved', 'my contributions', 'what did i work on'
        ]

        # Get stats keywords
        stats_keywords = [
            'my progress', 'my stats', 'how am i doing', 'my performance',
            'my statistics', 'show progress', 'my score', 'my level'
        ]

        # Get advice keywords
        advice_keywords = [
            'how do i', 'how to', 'help with', 'stuck on', 'debug', 'error',
            'fix', 'solve', 'problem with', 'issue with', 'trouble with'
        ]

        # Extract entities
        entities = self.extract_entities(user_message, intent=None)

        # Classify based on keywords
        for keyword in search_keywords:
            if keyword in message_lower:
                return {
                    'intent': 'search_issues',
                    'confidence': 0.75,
                    'entities': entities
                }

        for keyword in history_keywords:
            if keyword in message_lower:
                return {
                    'intent': 'view_history',
                    'confidence': 0.75,
                    'entities': entities
                }

        for keyword in stats_keywords:
            if keyword in message_lower:
                return {
                    'intent': 'get_stats',
                    'confidence': 0.75,
                    'entities': entities
                }

        for keyword in advice_keywords:
            if keyword in message_lower:
                return {
                    'intent': 'get_advice',
                    'confidence': 0.75,
                    'entities': entities
                }

        # Default to general_question
        return {
            'intent': 'general_question',
            'confidence': 0.6,
            'entities': entities
        }

    def extract_entities(self, user_message, intent=None):
        """
        Extract entities from user message using keyword matching.

        Entities:
        - language: Programming language (Python, JavaScript, etc.)
        - difficulty: Difficulty level (beginner, easy, medium, hard, advanced)
        - topic: Specific topic mentioned
        - time_period: Time reference (recent, this week, etc.)
        """
        message_lower = user_message.lower()
        entities = {}

        # Language detection
        languages = {
            'python': ['python', 'py', 'django', 'flask'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular'],
            'java': ['java'],
            'typescript': ['typescript', 'ts'],
            'go': ['go', 'golang'],
            'rust': ['rust'],
            'ruby': ['ruby', 'rails'],
            'php': ['php', 'laravel'],
            'c++': ['c++', 'cpp'],
            'c': ['c programming'],
            'swift': ['swift', 'ios'],
            'kotlin': ['kotlin', 'android']
        }

        for lang, keywords in languages.items():
            for keyword in keywords:
                if keyword in message_lower:
                    entities['language'] = lang.capitalize()
                    break
            if 'language' in entities:
                break

        # Difficulty detection
        difficulty_keywords = {
            'beginner': ['beginner', 'easy', 'simple', 'first', 'starter'],
            'medium': ['medium', 'intermediate', 'moderate'],
            'hard': ['hard', 'difficult', 'advanced', 'complex', 'challenging']
        }

        for level, keywords in difficulty_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    entities['difficulty'] = level
                    break
            if 'difficulty' in entities:
                break

        # Time period detection
        time_keywords = {
            'recent': ['recent', 'recently', 'latest', 'new'],
            'this week': ['this week', 'past week'],
            'this month': ['this month', 'past month'],
            'all time': ['all time', 'total', 'overall']
        }

        for period, keywords in time_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    entities['time_period'] = period
                    break
            if 'time_period' in entities:
                break

        # Topic extraction (simple - just capture key technical terms)
        technical_terms = [
            'api', 'database', 'cors', 'authentication', 'testing', 'deployment',
            'docker', 'git', 'css', 'html', 'redux', 'graphql', 'rest',
            'debugging', 'performance', 'security', 'ui', 'backend', 'frontend'
        ]

        for term in technical_terms:
            if term in message_lower:
                entities['topic'] = term.upper() if len(term) <= 4 else term.capitalize()
                break

        return entities


# Global intent classifier instance
_intent_classifier = None

def get_intent_classifier():
    """Get or create the global intent classifier."""
    global _intent_classifier
    if _intent_classifier is None:
        _intent_classifier = IntentClassifier()
    return _intent_classifier
