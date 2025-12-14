"""
Database Models
===============
Defines the structure of our database tables.

Tables:
- User: Stores user accounts
- SolvedIssue: Tracks issues the user has solved
- UserSkill: Tracks user's skill levels per language
- IssueCache: Caches GitHub issues
- ChatSession: Tracks chat sessions for conversation management
- Conversation: Stores individual chat messages
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()


class User(UserMixin, db.Model):
    """
    User account table.
    
    UserMixin adds: is_authenticated, is_active, is_anonymous, get_id()
    These are required by Flask-Login.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)  # Login username
    password_hash = db.Column(db.String(128), nullable=False)         # Hashed password
    github_username = db.Column(db.String(80), nullable=True)         # Their GitHub username
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - one user has many solved issues, skills, and chat sessions
    solved_issues = db.relationship('SolvedIssue', backref='user', lazy=True)
    skills = db.relationship('UserSkill', backref='user', lazy=True)
    chat_sessions = db.relationship('ChatSession', backref='user', lazy=True, cascade='all, delete-orphan')
    conversations = db.relationship('Conversation', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'


class SolvedIssue(db.Model):
    """
    Tracks issues that a user has marked as solved/completed.
    
    This helps us:
    1. Not recommend the same issue twice
    2. Track difficulty patterns
    3. Build user history for RAG
    """
    __tablename__ = 'solved_issues'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Issue details
    issue_url = db.Column(db.String(500), nullable=False)
    issue_title = db.Column(db.String(500), nullable=False)
    repo_name = db.Column(db.String(200), nullable=False)
    language = db.Column(db.String(50), nullable=True)
    
    # User feedback
    difficulty_rating = db.Column(db.Integer, nullable=True)  # 1-5 scale
    user_notes = db.Column(db.Text, nullable=True)            # Optional notes
    
    # Timestamps
    solved_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SolvedIssue {self.issue_title[:30]}>'
    
    def to_dict(self):
        """Convert to dictionary for RAG/JSON use."""
        return {
            'issue_url': self.issue_url,
            'issue_title': self.issue_title,
            'repo_name': self.repo_name,
            'language': self.language,
            'difficulty_rating': self.difficulty_rating,
            'user_notes': self.user_notes,
            'solved_at': self.solved_at.isoformat() if self.solved_at else None
        }


class UserSkill(db.Model):
    """
    Tracks user's skill level per programming language.
    
    Updated as they solve issues:
    - Solve easy Python issue → Python skill +1
    - Solve hard JavaScript issue → JavaScript skill +3
    """
    __tablename__ = 'user_skills'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    language = db.Column(db.String(50), nullable=False)
    skill_level = db.Column(db.Integer, default=1)  # 1-10 scale
    issues_solved = db.Column(db.Integer, default=0)  # Count of solved issues
    
    # Ensure one skill entry per language per user
    __table_args__ = (db.UniqueConstraint('user_id', 'language'),)
    
    def __repr__(self):
        return f'<UserSkill {self.language}: {self.skill_level}>'


class IssueCache(db.Model):
    """
    Cache for GitHub issues.

    Stores issues we've fetched so we don't hit API limits.
    Also used for RAG - we embed and search these.
    """
    __tablename__ = 'issue_cache'

    id = db.Column(db.Integer, primary_key=True)
    issue_url = db.Column(db.String(500), unique=True, nullable=False)
    issue_title = db.Column(db.String(500), nullable=False)
    repo_name = db.Column(db.String(200), nullable=False)
    language = db.Column(db.String(50), nullable=True)
    labels = db.Column(db.Text, nullable=True)  # JSON string of labels
    body = db.Column(db.Text, nullable=True)
    difficulty_estimate = db.Column(db.Integer, nullable=True)  # 1-5

    # When we fetched it
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<IssueCache {self.repo_name}>'

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'issue_url': self.issue_url,
            'issue_title': self.issue_title,
            'repo_name': self.repo_name,
            'language': self.language,
            'labels': self.labels,
            'body': self.body,
            'difficulty_estimate': self.difficulty_estimate
        }


class ChatSession(db.Model):
    """
    Tracks chat sessions for conversation management.

    Each session represents a continuous conversation between a user
    and the chatbot. Sessions help maintain context and manage
    conversation history efficiently.
    """
    __tablename__ = 'chat_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), unique=True, nullable=False)  # UUID
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Session metadata
    summary = db.Column(db.Text, nullable=True)  # Auto-generated summary for long conversations
    total_messages = db.Column(db.Integer, default=0)
    total_tokens_used = db.Column(db.Integer, default=0)

    # Relationships
    messages = db.relationship('Conversation', backref='session', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ChatSession {self.session_id[:8]}... ({self.total_messages} messages)>'

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'summary': self.summary,
            'total_messages': self.total_messages,
            'total_tokens_used': self.total_tokens_used
        }


class Conversation(db.Model):
    """
    Stores individual chat messages.

    Each message is part of a chat session and contains the full
    conversation history between user and assistant.
    """
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('chat_sessions.session_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Message content
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)

    # Message metadata (JSON): intent, tools_used, sources, entities, etc.
    message_metadata = db.Column(db.JSON, nullable=True)

    # Timestamps and usage
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tokens_used = db.Column(db.Integer, default=0)

    # Index for fast queries by session and time
    __table_args__ = (db.Index('idx_session_created', 'session_id', 'created_at'),)

    def __repr__(self):
        content_preview = self.content[:30] + '...' if len(self.content) > 30 else self.content
        return f'<Conversation {self.role}: {content_preview}>'

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'role': self.role,
            'content': self.content,
            'message_metadata': self.message_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'tokens_used': self.tokens_used
        }
