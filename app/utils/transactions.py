"""
Transaction management utilities.
Provides decorators and context managers for database transactions.
"""

from functools import wraps
from typing import Callable, Any
from app import db
from flask import current_app


def transactional(func: Callable) -> Callable:
    """
    Decorator to wrap a function in a database transaction.
    
    Automatically commits on success, rolls back on exception.
    
    Usage:
        @transactional
        def create_something():
            # Database operations
            return result
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            db.session.commit()
            return result
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Transaction failed in {func.__name__}: {e}")
            raise
    
    return wrapper


class Transaction:
    """
    Context manager for database transactions.
    
    Usage:
        with Transaction():
            # Database operations
            # Auto-commits on success, rolls back on exception
    """
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # No exception - commit
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Transaction commit failed: {e}")
                raise
        else:
            # Exception occurred - rollback
            db.session.rollback()
            current_app.logger.error(f"Transaction rolled back due to: {exc_val}")
        return False  # Don't suppress exceptions


def safe_transaction(func: Callable) -> Callable:
    """
    Decorator for safe transactions that don't raise exceptions.
    
    Returns a tuple of (success: bool, result: Any, error: str)
    
    Usage:
        @safe_transaction
        def create_something():
            # Database operations
            return result
        
        success, result, error = create_something()
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            db.session.commit()
            return True, result, None
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            current_app.logger.error(f"Safe transaction failed in {func.__name__}: {error_msg}")
            return False, None, error_msg
    
    return wrapper

