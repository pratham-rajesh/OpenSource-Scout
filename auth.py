"""
Authentication Module
=====================
Handles user registration and login.

Uses simple username/password authentication.
Passwords are hashed (never stored as plain text).
"""

from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User


def create_user(username, password, github_username=None):
    """
    Create a new user account.
    
    Parameters:
    - username: Login username
    - password: Plain text password (will be hashed)
    - github_username: Optional GitHub username
    
    Returns:
    - User object if successful
    - None if username already exists
    """
    # Check if username already exists
    existing = User.query.filter_by(username=username).first()
    if existing:
        return None
    
    # Create new user with hashed password
    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        github_username=github_username
    )
    
    db.session.add(user)
    db.session.commit()
    
    return user


def verify_user(username, password):
    """
    Verify user credentials.
    
    Parameters:
    - username: Login username
    - password: Plain text password
    
    Returns:
    - User object if credentials are valid
    - None if invalid
    """
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password_hash, password):
        return user
    
    return None


def update_github_username(user_id, github_username):
    """
    Update user's GitHub username.
    
    Parameters:
    - user_id: User's ID
    - github_username: New GitHub username
    
    Returns:
    - True if successful
    - False if failed
    """
    user = User.query.get(user_id)
    if user:
        user.github_username = github_username
        db.session.commit()
        return True
    return False


def get_user_by_id(user_id):
    """Get user by ID."""
    return User.query.get(user_id)
