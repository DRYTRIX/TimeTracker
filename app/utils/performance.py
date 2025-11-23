"""
Performance monitoring utilities.
"""

from typing import Callable, Any
from functools import wraps
import time
from flask import current_app, g


def measure_time(func: Callable) -> Callable:
    """
    Decorator to measure function execution time.
    
    Usage:
        @measure_time
        def slow_function():
            # Code
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.time() - start_time
            current_app.logger.debug(
                f"{func.__name__} took {elapsed:.4f} seconds"
            )
            # Store in request context if available
            if hasattr(g, 'performance_metrics'):
                g.performance_metrics[func.__name__] = elapsed
            else:
                g.performance_metrics = {func.__name__: elapsed}
    
    return wrapper


def log_slow_queries(threshold: float = 1.0):
    """
    Decorator to log slow database queries.
    
    Args:
        threshold: Time threshold in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start_time
                if elapsed > threshold:
                    current_app.logger.warning(
                        f"Slow query in {func.__name__}: {elapsed:.4f} seconds "
                        f"(threshold: {threshold}s)"
                    )
        
        return wrapper
    return decorator


class PerformanceMonitor:
    """Context manager for performance monitoring"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        current_app.logger.info(
            f"Performance: {self.operation_name} took {elapsed:.4f} seconds"
        )
        return False


def get_performance_metrics() -> dict:
    """
    Get performance metrics from request context.
    
    Returns:
        dict with performance metrics
    """
    if hasattr(g, 'performance_metrics'):
        return g.performance_metrics
    return {}

