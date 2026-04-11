"""
Clearance request models
"""

from datetime import datetime
from app.models.user import db

class ClearanceRequest(db.Model):
    """Clearance request model"""
    __tablename__ = 'clearance_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    request_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.Enum('Pending', 'Approved', 'Rejected', name='request_status'), 
                      default='Pending')
    payment_receipt = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(20), nullable=True)
    payment_amount = db.Column(db.Numeric(10, 2), nullable=True)
    reference_number = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'request_type': self.request_type,
            'status': self.status,
            'payment_receipt': self.payment_receipt,
            'payment_method': self.payment_method,
            'payment_amount': float(self.payment_amount) if self.payment_amount else None,
            'reference_number': self.reference_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'student_name': self.student.full_name if self.student else None
        }


class Notification(db.Model):
    """Notification model"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    staff_name = db.Column(db.String(200), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    phase = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'staff_name': self.staff_name,
            'action': self.action,
            'phase': self.phase,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
