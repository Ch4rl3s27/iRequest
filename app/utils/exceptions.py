"""
Custom exceptions for the iRequest application
"""

class iRequestException(Exception):
    """Base exception for iRequest application"""
    pass

class ValidationError(iRequestException):
    """Validation error"""
    pass

class AuthenticationError(iRequestException):
    """Authentication error"""
    pass

class AuthorizationError(iRequestException):
    """Authorization error"""
    pass

class DatabaseError(iRequestException):
    """Database error"""
    pass

class EmailError(iRequestException):
    """Email service error"""
    pass

class FileUploadError(iRequestException):
    """File upload error"""
    pass

class PaymentError(iRequestException):
    """Payment processing error"""
    pass
