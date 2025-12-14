"""
Get User Stats Tool
===================
Retrieves user statistics and progress metrics.
"""

from models import SolvedIssue, UserSkill, db
from datetime import datetime, timedelta


def get_user_stats(user_id, time_period="all", language=None):
    """
    Get user statistics and progress.

    Parameters:
    - user_id: User ID
    - time_period: "all", "week", "month", or "recent"
    - language: Optional language filter

    Returns:
    - dict with statistics
    """
    try:
        # Build query
        query = SolvedIssue.query.filter_by(user_id=user_id)

        # Filter by time period
        if time_period == "week":
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            query = query.filter(SolvedIssue.solved_at >= cutoff_date)
        elif time_period == "month":
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            query = query.filter(SolvedIssue.solved_at >= cutoff_date)
        elif time_period == "recent":
            cutoff_date = datetime.utcnow() - timedelta(days=14)
            query = query.filter(SolvedIssue.solved_at >= cutoff_date)

        # Filter by language
        if language:
            query = query.filter(SolvedIssue.language.ilike(f"%{language}%"))

        # Get all matching issues
        issues = query.all()

        # Calculate statistics
        total_solved = len(issues)

        if total_solved == 0:
            return {
                'total_solved': 0,
                'languages': [],
                'avg_difficulty': 0,
                'recent_count': 0,
                'top_repos': [],
                'time_period': time_period
            }

        # Language distribution
        language_counts = {}
        for issue in issues:
            lang = issue.language or "Unknown"
            language_counts[lang] = language_counts.get(lang, 0) + 1

        top_languages = sorted(language_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        # Average difficulty
        difficulties = [issue.difficulty_rating for issue in issues if issue.difficulty_rating]
        avg_difficulty = round(sum(difficulties) / len(difficulties), 1) if difficulties else 0

        # Recent activity (last 7 days)
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        recent_count = sum(1 for issue in issues if issue.solved_at >= recent_cutoff)

        # Top repositories
        repo_counts = {}
        for issue in issues:
            repo = issue.repo_name
            repo_counts[repo] = repo_counts.get(repo, 0) + 1

        top_repos = sorted(repo_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        # Get skill levels
        skills = UserSkill.query.filter_by(user_id=user_id).all()
        skill_levels = {skill.language: skill.skill_level for skill in skills}

        return {
            'total_solved': total_solved,
            'languages': top_languages,
            'avg_difficulty': avg_difficulty,
            'recent_count': recent_count,
            'top_repos': top_repos,
            'skill_levels': skill_levels,
            'time_period': time_period
        }

    except Exception as e:
        print(f"Get user stats error: {e}")
        return {
            'total_solved': 0,
            'languages': [],
            'avg_difficulty': 0,
            'recent_count': 0,
            'top_repos': [],
            'time_period': time_period
        }
