"""
Get Skill Analysis Tool
========================
Analyzes user's skill progression and provides insights.
"""

from models import UserSkill, SolvedIssue, db
from datetime import datetime, timedelta


def get_skill_analysis(user_id, language=None):
    """
    Analyze user's skill levels and progression.

    Parameters:
    - user_id: User ID
    - language: Optional language filter

    Returns:
    - dict with skill analysis
    """
    try:
        # Get user skills
        skills_query = UserSkill.query.filter_by(user_id=user_id)

        if language:
            skills_query = skills_query.filter(UserSkill.language.ilike(f"%{language}%"))

        skills = skills_query.all()

        if not skills:
            return {
                'skills': [],
                'recommendations': ["Start solving issues to build your skills!"],
                'strongest_language': None,
                'growth_areas': []
            }

        # Analyze each skill
        skill_details = []
        for skill in skills:
            # Get recent issues for this language
            recent_cutoff = datetime.utcnow() - timedelta(days=30)
            recent_issues = SolvedIssue.query.filter_by(
                user_id=user_id,
                language=skill.language
            ).filter(SolvedIssue.solved_at >= recent_cutoff).count()

            skill_details.append({
                'language': skill.language,
                'level': skill.skill_level,
                'total_solved': skill.issues_solved,
                'recent_activity': recent_issues,
                'progress': 'Active' if recent_issues > 0 else 'Inactive'
            })

        # Sort by skill level
        skill_details.sort(key=lambda x: x['level'], reverse=True)

        # Find strongest language
        strongest = skill_details[0] if skill_details else None

        # Find growth areas (low level but active, or high level but inactive)
        growth_areas = []
        for skill in skill_details:
            if skill['level'] < 5 and skill['recent_activity'] > 0:
                growth_areas.append(f"{skill['language']} (Level {skill['level']}) - Keep practicing!")
            elif skill['level'] >= 5 and skill['recent_activity'] == 0:
                growth_areas.append(f"{skill['language']} (Level {skill['level']}) - Stay active to maintain your level!")

        # Generate recommendations
        recommendations = []
        if strongest:
            if strongest['level'] < 10:
                recommendations.append(f"Focus on {strongest['language']} to reach Level {strongest['level'] + 1}")

        # Recommend new languages
        if len(skill_details) < 3:
            recommendations.append("Try learning a new language to diversify your skills")

        # Recommend difficulty progression
        avg_level = sum(s['level'] for s in skill_details) / len(skill_details)
        if avg_level < 3:
            recommendations.append("Focus on beginner-friendly issues to build confidence")
        elif avg_level < 6:
            recommendations.append("Try medium difficulty issues to challenge yourself")
        else:
            recommendations.append("Take on advanced issues to become an expert")

        return {
            'skills': skill_details,
            'recommendations': recommendations,
            'strongest_language': strongest['language'] if strongest else None,
            'growth_areas': growth_areas[:3]  # Top 3 growth areas
        }

    except Exception as e:
        print(f"Get skill analysis error: {e}")
        return {
            'skills': [],
            'recommendations': [],
            'strongest_language': None,
            'growth_areas': []
        }
