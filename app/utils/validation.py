"""
Input validation utilities.
Provides consistent validation across the application.
"""

from typing import Any, Dict, Optional, List
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from flask import request
from marshmallow import ValidationError


def validate_required(data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """
    Validate that required fields are present.
    
    Args:
        data: Dictionary to validate
        fields: List of required field names
        
    Returns:
        dict with 'valid' (bool) and 'errors' (list) keys
        
    Raises:
        ValidationError if validation fails
    """
    errors = []
    for field in fields:
        if field not in data or data[field] is None:
            errors.append(f"{field} is required")
    
    if errors:
        raise ValidationError(errors)
    
    return {'valid': True, 'errors': []}


def validate_date_range(start_date: Any, end_date: Any) -> bool:
    """
    Validate that end_date is after start_date.
    
    Args:
        start_date: Start date (datetime, date, or string)
        end_date: End date (datetime, date, or string)
        
    Returns:
        True if valid
        
    Raises:
        ValidationError if invalid
    """
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()
    
    if end_date <= start_date:
        raise ValidationError('end_date must be after start_date')
    
    return True


def validate_decimal(value: Any, min_value: Optional[Decimal] = None, max_value: Optional[Decimal] = None) -> Decimal:
    """
    Validate and convert a value to Decimal.
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Decimal value
        
    Raises:
        ValidationError if invalid
    """
    try:
        decimal_value = Decimal(str(value))
    except (ValueError, InvalidOperation, TypeError):
        raise ValidationError(f"Invalid decimal value: {value}")
    
    if min_value is not None and decimal_value < min_value:
        raise ValidationError(f"Value must be at least {min_value}")
    
    if max_value is not None and decimal_value > max_value:
        raise ValidationError(f"Value must be at most {max_value}")
    
    return decimal_value


def validate_integer(value: Any, min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
    """
    Validate and convert a value to integer.
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Integer value
        
    Raises:
        ValidationError if invalid
    """
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid integer value: {value}")
    
    if min_value is not None and int_value < min_value:
        raise ValidationError(f"Value must be at least {min_value}")
    
    if max_value is not None and int_value > max_value:
        raise ValidationError(f"Value must be at most {max_value}")
    
    return int_value


def validate_string(value: Any, min_length: Optional[int] = None, max_length: Optional[int] = None) -> str:
    """
    Validate and convert a value to string.
    
    Args:
        value: Value to validate
        min_length: Minimum string length
        max_length: Maximum string length
        
    Returns:
        String value
        
    Raises:
        ValidationError if invalid
    """
    if value is None:
        raise ValidationError("String value cannot be None")
    
    str_value = str(value).strip()
    
    if min_length is not None and len(str_value) < min_length:
        raise ValidationError(f"String must be at least {min_length} characters")
    
    if max_length is not None and len(str_value) > max_length:
        raise ValidationError(f"String must be at most {max_length} characters")
    
    return str_value


def validate_email(email: str) -> str:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Validated email address
        
    Raises:
        ValidationError if invalid
    """
    import re
    
    email = email.strip().lower()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        raise ValidationError(f"Invalid email address: {email}")
    
    return email


def validate_json_request() -> Dict[str, Any]:
    """
    Validate that request contains valid JSON.
    
    Returns:
        Parsed JSON data
        
    Raises:
        ValidationError if invalid
    """
    if not request.is_json:
        raise ValidationError("Request must contain JSON data")
    
    data = request.get_json()
    if data is None:
        raise ValidationError("Request JSON is empty")
    
    return data


def sanitize_input(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize user input by removing dangerous characters.
    
    Args:
        value: Input string
        max_length: Maximum length to truncate to
        
    Returns:
        Sanitized string
    """
    import bleach
    
    # Remove HTML tags and dangerous characters
    sanitized = bleach.clean(value, tags=[], strip=True)
    
    # Truncate if needed
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized

