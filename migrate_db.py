"""
Database Migration Script
=========================
Creates new tables for ChatSession and Conversation models.

Run this script to add the new tables to the existing database
without affecting existing data.
"""

from app import app
from models import db, ChatSession, Conversation

def migrate():
    """Create new tables for conversation management."""
    with app.app_context():
        # Create only the new tables (doesn't affect existing ones)
        db.create_all()
        print("✓ Database migration completed successfully!")
        print("✓ ChatSession and Conversation tables created")

if __name__ == '__main__':
    migrate()
