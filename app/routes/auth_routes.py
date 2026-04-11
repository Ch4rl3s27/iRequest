"""
Authentication routes
"""

from flask import Blueprint, request, jsonify, session, render_template
from app.services import AuthService
from app.utils import ValidationError, AuthenticationError, log_error, create_response

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    try:
        form = request.form
        email = form.get('email', '').strip().lower()
        password = form.get('password', '')

        if not email or not password:
            return jsonify(create_response(False, "Please enter both email and password.")), 400

        success, user_type, user_data = AuthService.authenticate_user(email, password)
        
        if success:
            # Determine redirect URL based on user type
            if user_type == 'student':
                redirect_url = "/student_dashboard.html"
            else:  # staff
                from app.utils.helpers import get_department_dashboard
                redirect_url = get_department_dashboard(user_data.get('department', 'Dean'))
            
            return jsonify(create_response(True, "Login successful", {"redirect": redirect_url}))
        
    except ValidationError as e:
        return jsonify(create_response(False, str(e))), 400
    except AuthenticationError as e:
        return jsonify(create_response(False, str(e))), 401
    except Exception as e:
        log_error("Login error", e)
        return jsonify(create_response(False, "Login failed. Please try again.")), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Handle user logout"""
    try:
        success = AuthService.logout_user()
        if success:
            return jsonify(create_response(True, "Logged out successfully"))
        else:
            return jsonify(create_response(False, "Logout failed")), 500
    except Exception as e:
        log_error("Logout error", e)
        return jsonify(create_response(False, "Logout failed")), 500


@auth_bp.route('/api/current-user', methods=['GET'])
def get_current_user():
    """Get current logged-in user"""
    try:
        user = AuthService.get_current_user()
        if user:
            return jsonify(create_response(True, "User found", user))
        else:
            return jsonify(create_response(False, "No user logged in")), 401
    except Exception as e:
        log_error("Get current user error", e)
        return jsonify(create_response(False, "Failed to get user info")), 500
