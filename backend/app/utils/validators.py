import re
from pydantic import EmailStr, field_validator
from typing import Any


class EmailValidator:
    """Strict email validation."""
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email format."""
        # Additional validation beyond Pydantic's EmailStr
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValueError("Invalid email format")
        return email.lower()


class PasswordValidator:
    """Password complexity validation."""
    
    @staticmethod
    def validate_password(password: str) -> str:
        """
        Validate password complexity.
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', password):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            raise ValueError("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError("Password must contain at least one special character")
        
        return password


def sanitize_string(value: str) -> str:
    """Sanitize string input by removing potentially harmful characters."""
    # Remove null bytes and control characters
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)
    return sanitized.strip()
