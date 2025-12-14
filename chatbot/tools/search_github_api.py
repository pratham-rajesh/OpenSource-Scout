"""
Search GitHub API Tool
======================
Searches GitHub API for good first issues in real-time.
"""

from github_helper import search_good_first_issues


def search_github_api(query=None, language=None, difficulty=None, max_results=25):
    """
    Search GitHub API for good first issues.

    Parameters:
    - query: Optional search query text
    - language: Programming language filter
    - difficulty: Difficulty level (maps to labels)
    - max_results: Maximum number of results (default: 25)

    Returns:
    - List of issue dicts with title, repo, url, language, labels, body
    """
    # Build language list for search
    languages = []
    if language:
        languages = [language]

    try:
        # Use existing GitHub helper
        issues = search_good_first_issues(languages or [""], max_issues=max_results)

        # Filter by difficulty if specified
        if difficulty:
            difficulty_lower = difficulty.lower()
            filtered_issues = []

            for issue in issues:
                issue_labels = [label.lower() for label in issue.get('labels', [])]
                title_lower = issue.get('title', '').lower()
                body_lower = issue.get('body', '').lower()

                # Check if difficulty matches
                if difficulty_lower in ['beginner', 'easy']:
                    easy_terms = ['beginner', 'easy', 'good-first-issue', 'good first issue', 'starter']
                    if any(term in issue_labels or term in title_lower for term in easy_terms):
                        filtered_issues.append(issue)
                elif difficulty_lower in ['medium', 'intermediate']:
                    if not any(term in issue_labels for term in ['beginner', 'easy', 'hard', 'advanced']):
                        filtered_issues.append(issue)
                elif difficulty_lower in ['hard', 'advanced']:
                    hard_terms = ['hard', 'advanced', 'challenging']
                    if any(term in issue_labels or term in title_lower for term in hard_terms):
                        filtered_issues.append(issue)
                else:
                    filtered_issues.append(issue)

            issues = filtered_issues

        return issues[:max_results]

    except Exception as e:
        print(f"GitHub API search error: {e}")
        return []
