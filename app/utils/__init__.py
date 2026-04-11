"""
Utilities package initialization
"""

from app.utils.exceptions import (
    iRequestException, ValidationError, AuthenticationError, 
    AuthorizationError, DatabaseError, EmailError, FileUploadError, PaymentError
)
from app.utils.validators import (
    validate_email, validate_password, validate_required, 
    validate_string_length, validate_phone_number, validate_file_extension
)
from app.utils.helpers import (
    setup_logging, log_error, log_info, get_department_dashboard,
    ensure_directory_exists, safe_get_env, create_response
)

__all__ = [
    'iRequestException', 'ValidationError', 'AuthenticationError', 
    'AuthorizationError', 'DatabaseError', 'EmailError', 'FileUploadError', 'PaymentError',
    'validate_email', 'validate_password', 'validate_required', 
    'validate_string_length', 'validate_phone_number', 'validate_file_extension',
    'setup_logging', 'log_error', 'log_info', 'get_department_dashboard',
    'ensure_directory_exists', 'safe_get_env', 'create_response'
]