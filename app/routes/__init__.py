"""
Routes package initialization
"""

from app.routes.auth_routes import auth_bp
from app.routes.student_routes import student_bp

__all__ = ['auth_bp', 'student_bp']