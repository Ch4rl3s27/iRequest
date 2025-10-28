"""
Authentication routes
"""

from flask import Blueprint, request, jsonify, session, render_template
from werkzeug.security import check_password_hash
from app.models.database import get_db_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    form = request.form
    email = form.get('email', '').strip().lower()
    password = form.get('password', '')

    if not email or not password:
        return jsonify({"ok": False, "message": "Please enter both email and password."}), 400

    try:
        mysql = get_db_connection()
        if mysql is None:
            return jsonify({"ok": False, "message": "Database not available"}), 500
            
        cur = mysql.connection.cursor()
        
        # Check if user is a student
        cur.execute("SELECT id, first_name, last_name, password_hash, COALESCE(otp_verified, 0) AS otp_verified FROM students WHERE email = %s", (email,))
        student = cur.fetchone()
        
        if student and check_password_hash(student['password_hash'], password):
            session['student_email'] = email
            session.permanent = True
            cur.close()
            return jsonify({"ok": True, "redirect": "/student_dashboard.html"})
        
        # Check staff
        cur.execute("SELECT id, department, first_name, last_name, password_hash, status FROM staff WHERE email = %s", (email,))
        staff = cur.fetchone()
        cur.close()
        
        if staff and check_password_hash(staff['password_hash'], password):
            if staff['status'] != 'Approved':
                return jsonify({"ok": False, "message": "Account not approved yet. Please wait for admin approval."}), 403
            
            session['staff_email'] = email
            session['staff_department'] = staff['department']
            session.permanent = True
            
            # Redirect based on department
            redirect_url = get_department_dashboard(staff['department'])
            return jsonify({"ok": True, "redirect": redirect_url})
        
        return jsonify({"ok": False, "message": "Invalid email or password."}), 401
        
    except Exception as e:
        return jsonify({"ok": False, "message": f"Login error: {str(e)}"}), 500

def get_department_dashboard(department):
    """Get dashboard URL based on department"""
    dashboard_map = {
        'Registrar': '/Registrar_Dashboard.html',
        'Dean': '/Dean_Dashboard.html',
        'Dean_CS': '/Dean_CS_Dashboard.html',
        'Dean_CoEd': '/Dean_CoEd_Dashboard.html',
        'Dean_HM': '/Dean_HM_Dashboard.html',
        'Accounting': '/Accounting_Dashboard.html',
        'Library': '/Library_Dashboard.html',
        'Guidance': '/GuidanceOffice_Dashboard.html',
        'Property_Custodian': '/PropertyCustodian_Dashboard.html',
        'Computer_Laboratory': '/ComputerLaboratory_Dashboard.html',
        'Student_Affairs': '/StudentAffairs_dashboard.html'
    }
    return dashboard_map.get(department, '/Dean_Dashboard.html')

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Handle user logout"""
    session.clear()
    return jsonify({"ok": True, "message": "Logged out successfully"})
