"""
Database models initialization
"""

from flask_sqlalchemy import SQLAlchemy
from app.models.user import Student, Staff
from app.models.clearance import ClearanceRequest, Notification

# Initialize SQLAlchemy
db = SQLAlchemy()

# Export all models
__all__ = ['db', 'Student', 'Staff', 'ClearanceRequest', 'Notification']