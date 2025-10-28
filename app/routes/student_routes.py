"""
Student routes
"""

from flask import Blueprint, request, jsonify, session
from app.services import AuthService
from app.models import db, Student, ClearanceRequest, Notification
from app.utils import ValidationError, AuthenticationError, log_error, create_response, validate_required

student_bp = Blueprint('student', __name__)

@student_bp.route('/api/student/me', methods=['GET'])
def get_student_info():
    """Get current student information"""
    try:
        user = AuthService.require_auth()
        if user['type'] != 'student':
            return jsonify(create_response(False, "Student access required")), 403
        
        student = Student.query.filter_by(email=session['student_email']).first()
        if not student:
            return jsonify(create_response(False, "Student not found")), 404
        
        return jsonify(create_response(True, "Student info retrieved", student.to_dict()))
        
    except AuthenticationError:
        return jsonify(create_response(False, "Authentication required")), 401
    except Exception as e:
        log_error("Get student info error", e)
        return jsonify(create_response(False, "Failed to get student info")), 500


@student_bp.route('/api/student/clearance', methods=['POST'])
def create_clearance_request():
    """Create new clearance request"""
    try:
        user = AuthService.require_auth()
        if user['type'] != 'student':
            return jsonify(create_response(False, "Student access required")), 403
        
        data = request.get_json()
        if not data:
            return jsonify(create_response(False, "No data provided")), 400
        
        # Validate required fields
        validate_required(data.get('request_type'), 'Request type')
        
        student = Student.query.filter_by(email=session['student_email']).first()
        if not student:
            return jsonify(create_response(False, "Student not found")), 404
        
        # Create clearance request
        clearance_request = ClearanceRequest(
            student_id=student.id,
            request_type=data['request_type'],
            payment_receipt=data.get('payment_receipt')
        )
        
        db.session.add(clearance_request)
        db.session.commit()
        
        return jsonify(create_response(True, "Clearance request created", clearance_request.to_dict()))
        
    except ValidationError as e:
        return jsonify(create_response(False, str(e))), 400
    except AuthenticationError:
        return jsonify(create_response(False, "Authentication required")), 401
    except Exception as e:
        log_error("Create clearance request error", e)
        db.session.rollback()
        return jsonify(create_response(False, "Failed to create clearance request")), 500


@student_bp.route('/api/student/requests', methods=['GET'])
def get_student_requests():
    """Get student's clearance requests"""
    try:
        user = AuthService.require_auth()
        if user['type'] != 'student':
            return jsonify(create_response(False, "Student access required")), 403
        
        student = Student.query.filter_by(email=session['student_email']).first()
        if not student:
            return jsonify(create_response(False, "Student not found")), 404
        
        requests = ClearanceRequest.query.filter_by(student_id=student.id).order_by(ClearanceRequest.created_at.desc()).all()
        requests_data = [req.to_dict() for req in requests]
        
        return jsonify(create_response(True, "Requests retrieved", requests_data))
        
    except AuthenticationError:
        return jsonify(create_response(False, "Authentication required")), 401
    except Exception as e:
        log_error("Get student requests error", e)
        return jsonify(create_response(False, "Failed to get requests")), 500


@student_bp.route('/api/student/notifications', methods=['GET'])
def get_student_notifications():
    """Get student notifications"""
    try:
        user = AuthService.require_auth()
        if user['type'] != 'student':
            return jsonify(create_response(False, "Student access required")), 403
        
        student = Student.query.filter_by(email=session['student_email']).first()
        if not student:
            return jsonify(create_response(False, "Student not found")), 404
        
        notifications = Notification.query.filter_by(student_id=student.id).order_by(Notification.created_at.desc()).all()
        notifications_data = [notif.to_dict() for notif in notifications]
        
        return jsonify(create_response(True, "Notifications retrieved", notifications_data))
        
    except AuthenticationError:
        return jsonify(create_response(False, "Authentication required")), 401
    except Exception as e:
        log_error("Get student notifications error", e)
        return jsonify(create_response(False, "Failed to get notifications")), 500
