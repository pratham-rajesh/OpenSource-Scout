"""
GitHub Helper Module
====================
Handles all GitHub API interactions:
- Fetch user profile
- Get user's languages
- Search for good first issues
- Get user's PR history
"""

import requests
import os
from datetime import datetime, timedelta

GITHUB_API = "https://api.github.com"


def get_headers():
    """Get headers for GitHub API requests."""
    token = os.getenv("GITHUB_TOKEN")
    # Only use token if it's not the placeholder value
    if token and token != "your_github_token_here":
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    return {"Accept": "application/vnd.github.v3+json"}


def get_user_info(username):
    """Get basic GitHub user info."""
    url = f"{GITHUB_API}/users/{username}"
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)

        # Better error handling
        if response.status_code == 404:
            print(f"GitHub user '{username}' not found (404)")
            return None
        elif response.status_code == 403:
            print(f"GitHub API rate limit exceeded. Add GITHUB_TOKEN to .env")
            return None
        elif response.status_code == 200:
            data = response.json()
            return {
                "name": data.get("name", username),
                "avatar": data.get("avatar_url", ""),
                "bio": data.get("bio", ""),
                "public_repos": data.get("public_repos", 0),
                "followers": data.get("followers", 0),
                "github_url": data.get("html_url", "")
            }
        else:
            print(f"GitHub API error: {response.status_code} - {response.text[:200]}")
            return None
    except requests.exceptions.Timeout:
        print(f"GitHub API timeout for user: {username}")
        return None
    except Exception as e:
        print(f"Error fetching user info: {e}")
        return None


def get_user_languages(username):
    """
    Get languages from user's repos.
    Returns: [("Python", 5), ("JavaScript", 3), ...] - language and repo count
    """
    url = f"{GITHUB_API}/users/{username}/repos"
    params = {"type": "owner", "sort": "updated", "per_page": 50}
    
    try:
        response = requests.get(url, headers=get_headers(), params=params)
        if response.status_code != 200:
            return []
        
        repos = response.json()
        language_count = {}
        
        for repo in repos:
            lang = repo.get("language")
            if lang:
                language_count[lang] = language_count.get(lang, 0) + 1
        
        # Sort by count and return as list of tuples
        sorted_langs = sorted(language_count.items(), key=lambda x: x[1], reverse=True)
        return sorted_langs
    
    except Exception as e:
        print(f"Error fetching languages: {e}")
        return []


def search_good_first_issues(languages, max_issues=30):
    """
    Search for good first issues in given languages.
    Returns list of issue dictionaries.
    """
    all_issues = []
    
    # Get just language names if passed as tuples
    if languages and isinstance(languages[0], tuple):
        languages = [lang[0] for lang in languages]
    
    if not languages:
        languages = [""]  # Search any language
    
    for lang in languages[:3]:
        query_parts = [
            'label:"good first issue"',
            "state:open",
            "is:issue"
        ]
        if lang:
            query_parts.append(f"language:{lang}")
        
        query = " ".join(query_parts)
        url = f"{GITHUB_API}/search/issues"
        params = {
            "q": query,
            "sort": "created",
            "order": "desc",
            "per_page": max_issues // max(len(languages[:3]), 1)
        }
        
        try:
            response = requests.get(url, headers=get_headers(), params=params)
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get("items", []):
                    repo_url = item.get("repository_url", "")
                    repo_name = "/".join(repo_url.split("/")[-2:]) if repo_url else "Unknown"
                    
                    issue = {
                        "title": item.get("title", "No title"),
                        "repo": repo_name,
                        "url": item.get("html_url", ""),
                        "language": lang if lang else "Any",
                        "labels": [label["name"] for label in item.get("labels", [])],
                        "body": item.get("body", "")[:500] if item.get("body") else "",
                        "created_at": item.get("created_at", ""),
                        "comments": item.get("comments", 0)
                    }
                    all_issues.append(issue)
                    
        except Exception as e:
            print(f"Error searching issues for {lang}: {e}")
    
    return all_issues


def get_user_pr_history(username, days=90):
    """
    Get user's Pull Request history.
    Returns PRs they've submitted to any repo.
    """
    # Search for PRs by this user
    query = f"author:{username} type:pr"
    url = f"{GITHUB_API}/search/issues"
    params = {
        "q": query,
        "sort": "created",
        "order": "desc",
        "per_page": 50
    }
    
    prs = []
    
    try:
        response = requests.get(url, headers=get_headers(), params=params)
        if response.status_code == 200:
            data = response.json()
            
            for item in data.get("items", []):
                pr = {
                    "title": item.get("title", ""),
                    "url": item.get("html_url", ""),
                    "state": item.get("state", ""),
                    "created_at": item.get("created_at", ""),
                    "merged": item.get("pull_request", {}).get("merged_at") is not None,
                    "repo": "/".join(item.get("repository_url", "").split("/")[-2:])
                }
                prs.append(pr)
    
    except Exception as e:
        print(f"Error fetching PR history: {e}")
    
    return prs


def get_pr_stats(username):
    """
    Get statistics about user's PRs.
    Returns: {total, merged, open, closed_not_merged}
    """
    prs = get_user_pr_history(username)
    
    stats = {
        "total": len(prs),
        "merged": sum(1 for pr in prs if pr.get("merged")),
        "open": sum(1 for pr in prs if pr.get("state") == "open"),
        "closed_not_merged": sum(1 for pr in prs if pr.get("state") == "closed" and not pr.get("merged"))
    }
    
    # Calculate success rate
    if stats["total"] > 0:
        stats["success_rate"] = round((stats["merged"] / stats["total"]) * 100, 1)
    else:
        stats["success_rate"] = 0
    
    return stats


def estimate_issue_difficulty(issue):
    """
    Estimate difficulty of an issue based on labels and content.
    Returns: 1-5 (1=easiest, 5=hardest)
    """
    labels = [l.lower() for l in issue.get("labels", [])]
    title = issue.get("title", "").lower()
    body = issue.get("body", "").lower()
    
    difficulty = 3  # Default medium
    
    # Easy indicators
    easy_terms = ["typo", "documentation", "docs", "readme", "beginner", "easy", 
                  "simple", "minor", "small", "first-timer", "good first issue"]
    for term in easy_terms:
        if term in labels or term in title:
            difficulty -= 1
            break
    
    # Hard indicators
    hard_terms = ["complex", "refactor", "architecture", "performance", "security",
                  "breaking", "major", "difficult", "advanced"]
    for term in hard_terms:
        if term in labels or term in title:
            difficulty += 1
            break
    
    # Longer body usually means more complex
    if len(body) > 1000:
        difficulty += 1
    
    # Clamp to 1-5
    return max(1, min(5, difficulty))
