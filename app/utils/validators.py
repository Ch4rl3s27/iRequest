"""
Validation utilities
"""

import re
from typing import Any, Optional
from app.utils.exceptions import ValidationError


def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email to validate
        
    Returns:
        True if valid email
    """
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def validate_password(password: str) -> bool:
    """
    Validate password strength
    
    Args:
        password: Password to validate
        
    Returns:
        True if valid password
    """
    if not password or not isinstance(password, str):
        return False
    
    # At least 6 characters
    return len(password) >= 6


def validate_required(value: Any, field_name: str) -> None:
    """
    Validate required field
    
    Args:
        value: Value to validate
        field_name: Name of the field for error message
        
    Raises:
        ValidationError: If value is empty or None
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field_name} is required")


def validate_string_length(value: str, min_length: int = 1, max_length: Optional[int] = None, 
                          field_name: str = "Field") -> None:
    """
    Validate string length
    
    Args:
        value: String to validate
        min_length: Minimum length
        max_length: Maximum length
        field_name: Name of the field for error message
        
    Raises:
        ValidationError: If length is invalid
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    
    if len(value) < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters")
    
    if max_length and len(value) > max_length:
        raise ValidationError(f"{field_name} must be no more than {max_length} characters")


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if valid phone number
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid length (7-15 digits)
    return 7 <= len(digits_only) <= 15


def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
    """
    Validate file extension
    
    Args:
        filename: Name of the file
        allowed_extensions: Set of allowed extensions
        
    Returns:
        True if extension is allowed
    """
    if not filename:
        return False
    
    # Get file extension
    if '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions
