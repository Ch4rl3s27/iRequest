"""
Authentication service
"""

from typing import Optional, Tuple, Dict, Any
from flask import session
from app.models import db, Student, Staff
from app.utils.validators import validate_email, validate_password
from app.utils.exceptions import ValidationError, AuthenticationError


class AuthService:
    """Authentication service class"""
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Authenticate user (student or staff)
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Tuple of (success, user_type, user_data)
        """
        try:
            # Validate inputs
            if not validate_email(email):
                raise ValidationError("Invalid email format")
            
            if not validate_password(password):
                raise ValidationError("Password must be at least 6 characters")
            
            # Check if user is a student
            student = Student.query.filter_by(email=email.lower().strip()).first()
            if student and student.check_password(password):
                if not student.otp_verified:
                    raise AuthenticationError("Account not verified. Please check your email for OTP.")
                
                # Set session
                session['student_email'] = student.email
                session['student_id'] = student.id
                session.permanent = True
                
                return True, 'student', student.to_dict()
            
            # Check if user is staff
            staff = Staff.query.filter_by(email=email.lower().strip()).first()
            if staff and staff.check_password(password):
                if staff.status != 'Approved':
                    raise AuthenticationError("Account not approved yet. Please wait for admin approval.")
                
                # Set session
                session['staff_email'] = staff.email
                session['staff_id'] = staff.id
                session['staff_department'] = staff.department
                session.permanent = True
                
                return True, 'staff', staff.to_dict()
            
            raise AuthenticationError("Invalid email or password")
            
        except (ValidationError, AuthenticationError):
            raise
        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}")
    
    @staticmethod
    def logout_user() -> bool:
        """Logout current user"""
        try:
            session.clear()
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        """Get current logged-in user"""
        try:
            # Check for student session
            if 'student_email' in session:
                student = Student.query.filter_by(email=session['student_email']).first()
                if student:
                    return {'type': 'student', 'data': student.to_dict()}
            
            # Check for staff session
            if 'staff_email' in session:
                staff = Staff.query.filter_by(email=session['staff_email']).first()
                if staff:
                    return {'type': 'staff', 'data': staff.to_dict()}
            
            return None
        except Exception:
            return None
    
    @staticmethod
    def require_auth() -> Dict[str, Any]:
        """Require authentication - raise exception if not authenticated"""
        user = AuthService.get_current_user()
        if not user:
            raise AuthenticationError("Authentication required")
        return user
