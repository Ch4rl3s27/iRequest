"""
Helper utilities
"""

import os
import logging
from typing import Optional, Dict, Any
from flask import current_app
from app.utils.exceptions import DatabaseError


def setup_logging() -> None:
    """Setup application logging"""
    if not current_app.debug:
        # Production logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s %(message)s'
        )
    else:
        # Development logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(name)s %(message)s'
        )


def log_error(message: str, exception: Optional[Exception] = None) -> None:
    """
    Log error message
    
    Args:
        message: Error message
        exception: Exception object
    """
    if exception:
        current_app.logger.error(f"{message}: {str(exception)}")
    else:
        current_app.logger.error(message)


def log_info(message: str) -> None:
    """
    Log info message
    
    Args:
        message: Info message
    """
    current_app.logger.info(message)


def get_department_dashboard(department: str) -> str:
    """
    Get dashboard URL based on department
    
    Args:
        department: Department name
        
    Returns:
        Dashboard URL
    """
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


def ensure_directory_exists(directory_path: str) -> None:
    """
    Ensure directory exists, create if it doesn't
    
    Args:
        directory_path: Path to directory
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)


def safe_get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Safely get environment variable
    
    Args:
        key: Environment variable key
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    """
    try:
        return os.environ.get(key, default)
    except Exception:
        return default


def create_response(success: bool, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create standardized API response
    
    Args:
        success: Whether operation was successful
        message: Response message
        data: Optional data to include
        
    Returns:
        Standardized response dictionary
    """
    response = {
        'ok': success,
        'message': message
    }
    
    if data is not None:
        response['data'] = data
    
    return response
