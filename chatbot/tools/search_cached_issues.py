"""
Search Cached Issues Tool
==========================
Searches locally cached GitHub issues for fast results.
"""

from models import IssueCache, db


def search_cached_issues(query=None, language=None, difficulty=None, limit=10):
    """
    Search cached issues in local database.

    Parameters:
    - query: Search query text (searches title and body)
    - language: Programming language filter
    - difficulty: Difficulty level (1-5)
    - limit: Maximum number of results (default: 10)

    Returns:
    - List of issue dicts
    """
    try:
        # Start with base query
        db_query = IssueCache.query

        # Filter by language
        if language:
            db_query = db_query.filter(IssueCache.language.ilike(f"%{language}%"))

        # Filter by difficulty
        if difficulty:
            # Map difficulty names to numbers
            difficulty_map = {
                'beginner': 1,
                'easy': 2,
                'medium': 3,
                'hard': 4,
                'advanced': 5
            }

            if isinstance(difficulty, str):
                difficulty_num = difficulty_map.get(difficulty.lower(), 3)
            else:
                difficulty_num = difficulty

            db_query = db_query.filter(IssueCache.difficulty_estimate == difficulty_num)

        # Search in title or body if query provided
        if query:
            search_pattern = f"%{query}%"
            db_query = db_query.filter(
                db.or_(
                    IssueCache.issue_title.ilike(search_pattern),
                    IssueCache.body.ilike(search_pattern),
                    IssueCache.labels.ilike(search_pattern)
                )
            )

        # Order by most recent
        db_query = db_query.order_by(IssueCache.fetched_at.desc())

        # Limit results
        issues = db_query.limit(limit).all()

        # Convert to dict format
        return [issue.to_dict() for issue in issues]

    except Exception as e:
        print(f"Cached issue search error: {e}")
        return []
