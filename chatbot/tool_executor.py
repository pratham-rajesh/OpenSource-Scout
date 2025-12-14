"""
Tool Executor
=============
Executes tools based on intent and entities.

Maps intents to appropriate tools and handles parallel execution.
"""

from chatbot.tools.search_cached_issues import search_cached_issues
from chatbot.tools.search_github_api import search_github_api
from chatbot.tools.get_user_stats import get_user_stats
from chatbot.tools.get_similar_solved import get_similar_solved
from chatbot.tools.get_skill_analysis import get_skill_analysis


class ToolExecutor:
    """
    Executes tools based on classified intent and extracted entities.

    Maps intents to appropriate tools and returns combined results.
    """

    def __init__(self):
        """Initialize tool executor."""
        pass

    def execute_tools(self, intent, entities, user_id):
        """
        Execute appropriate tools based on intent and entities.

        Parameters:
        - intent: Classified intent (search_issues, view_history, etc.)
        - entities: Extracted entities (language, difficulty, etc.)
        - user_id: Current user ID

        Returns:
        - dict with tool results
        """
        results = {}

        try:
            # Extract common entities
            language = entities.get('language')
            difficulty = entities.get('difficulty')
            time_period = entities.get('time_period', 'all')
            topic = entities.get('topic')

            # Execute tools based on intent
            if intent == 'search_issues':
                # Hybrid search: cached first, then API
                results['cached_issues'] = search_cached_issues(
                    query=topic,
                    language=language,
                    difficulty=difficulty,
                    limit=5
                )

                # If not enough cached results, search GitHub API
                if len(results.get('cached_issues', [])) < 5:
                    results['api_issues'] = search_github_api(
                        query=topic,
                        language=language,
                        difficulty=difficulty,
                        max_results=10
                    )
                else:
                    results['api_issues'] = []

                # Combine and deduplicate
                all_issues = results['cached_issues'] + results['api_issues']
                seen_urls = set()
                unique_issues = []
                for issue in all_issues:
                    url = issue.get('issue_url') or issue.get('url')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        unique_issues.append(issue)

                results['issues'] = unique_issues[:10]

            elif intent == 'view_history':
                # Get user's solved issues
                results['user_stats'] = get_user_stats(
                    user_id=user_id,
                    time_period=time_period,
                    language=language
                )

                # Get similar solved issues (for context)
                query = f"{language or 'programming'} {topic or ''}"
                results['similar_solved'] = get_similar_solved(
                    user_id=user_id,
                    query=query.strip(),
                    n_results=5
                )

            elif intent == 'get_stats':
                # Get comprehensive statistics
                results['user_stats'] = get_user_stats(
                    user_id=user_id,
                    time_period=time_period,
                    language=language
                )

                # Get skill analysis
                results['skill_analysis'] = get_skill_analysis(
                    user_id=user_id,
                    language=language
                )

            elif intent == 'get_advice':
                # Check if user has solved similar issues before
                query = f"{language or ''} {topic or ''} debugging help"
                results['similar_solved'] = get_similar_solved(
                    user_id=user_id,
                    query=query.strip(),
                    n_results=5
                )

                # Get user stats for context
                results['user_stats'] = get_user_stats(
                    user_id=user_id,
                    time_period='all',
                    language=language
                )

            elif intent == 'general_question':
                # For general questions, provide minimal context
                # Just get user's skill level for relevant language
                if language:
                    results['skill_analysis'] = get_skill_analysis(
                        user_id=user_id,
                        language=language
                    )

            return results

        except Exception as e:
            print(f"Tool execution error: {e}")
            return {}

    def format_tool_results(self, intent, tool_results):
        """
        Format tool results into human-readable text for LLM context.

        Parameters:
        - intent: The classified intent
        - tool_results: Results from execute_tools()

        Returns:
        - Formatted string for LLM context
        """
        try:
            formatted = []

            if intent == 'search_issues' and 'issues' in tool_results:
                issues = tool_results['issues']
                if issues:
                    formatted.append(f"Found {len(issues)} matching issues:\n")
                    for i, issue in enumerate(issues[:5], 1):
                        title = issue.get('issue_title') or issue.get('title', 'No title')
                        repo = issue.get('repo_name') or issue.get('repo', 'Unknown')
                        lang = issue.get('language', 'Unknown')
                        formatted.append(f"{i}. [{repo}] {title} (Language: {lang})")
                else:
                    formatted.append("No matching issues found.")

            elif intent in ['view_history', 'get_stats']:
                if 'user_stats' in tool_results:
                    stats = tool_results['user_stats']
                    formatted.append(f"User Statistics:")
                    formatted.append(f"- Total solved: {stats.get('total_solved', 0)} issues")
                    formatted.append(f"- Average difficulty: {stats.get('avg_difficulty', 0)}/5")
                    formatted.append(f"- Recent activity: {stats.get('recent_count', 0)} issues this week")

                    if stats.get('languages'):
                        langs = ', '.join([f"{lang} ({count})" for lang, count in stats['languages']])
                        formatted.append(f"- Top languages: {langs}")

                if 'skill_analysis' in tool_results:
                    analysis = tool_results['skill_analysis']
                    if analysis.get('strongest_language'):
                        formatted.append(f"- Strongest language: {analysis['strongest_language']}")

            elif intent == 'get_advice' and 'similar_solved' in tool_results:
                similar = tool_results['similar_solved']
                if similar:
                    formatted.append(f"You've solved {len(similar)} similar issues before:")
                    for i, issue_text in enumerate(similar[:3], 1):
                        preview = issue_text[:100] + "..." if len(issue_text) > 100 else issue_text
                        formatted.append(f"{i}. {preview}")

            return "\n".join(formatted) if formatted else "No relevant information found."

        except Exception as e:
            print(f"Format tool results error: {e}")
            return "Error formatting results."


# Global tool executor instance
_tool_executor = None

def get_tool_executor():
    """Get or create the global tool executor."""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor
