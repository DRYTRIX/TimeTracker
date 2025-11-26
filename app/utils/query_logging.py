"""
Database query logging and performance monitoring utilities.
Helps identify slow queries and N+1 problems.
"""

import logging
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager
from flask import current_app, g
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)
SLOW_QUERY_THRESHOLD = 0.1  # Log queries slower than 100ms


def enable_query_logging(app, slow_query_threshold: float = 0.1):
    """
    Enable SQL query logging for the Flask app.
    
    Args:
        app: Flask application instance
        slow_query_threshold: Threshold in seconds for logging slow queries
    """
    @event.listens_for(Engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time"""
        conn.info.setdefault('query_start_time', []).append(time.time())
    
    @event.listens_for(Engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Log query execution time"""
        total = time.time() - conn.info['query_start_time'].pop(-1)
        
        # Only log slow queries in production, all queries in development
        if app.config.get('FLASK_DEBUG') or total > slow_query_threshold:
            # Format parameters for logging (truncate long values)
            params_str = str(parameters)
            if len(params_str) > 200:
                params_str = params_str[:200] + "..."
            
            # Truncate long statements
            statement_str = statement
            if len(statement_str) > 500:
                statement_str = statement_str[:500] + "..."
            
            logger.debug(
                f"Query executed in {total:.4f}s: {statement_str} | Params: {params_str}"
            )
            
            # Track slow queries
            if total > slow_query_threshold:
                logger.warning(
                    f"SLOW QUERY ({total:.4f}s): {statement_str[:200]}..."
                )
                
                # Track in request context for reporting
                if not hasattr(g, 'slow_queries'):
                    g.slow_queries = []
                g.slow_queries.append({
                    'query': statement_str[:200],
                    'duration': total,
                    'parameters': params_str[:100]
                })


@contextmanager
def query_timer(operation_name: str):
    """
    Context manager to time a database operation.
    
    Usage:
        with query_timer("get_user_projects"):
            projects = Project.query.filter_by(user_id=user_id).all()
    
    Args:
        operation_name: Name of the operation being timed
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        if duration > SLOW_QUERY_THRESHOLD:
            logger.warning(f"Slow operation '{operation_name}': {duration:.4f}s")
        else:
            logger.debug(f"Operation '{operation_name}': {duration:.4f}s")


def get_query_stats() -> Dict[str, Any]:
    """
    Get query statistics for the current request.
    
    Returns:
        dict with query statistics
    """
    stats = {
        'slow_queries': getattr(g, 'slow_queries', []),
        'total_slow_queries': len(getattr(g, 'slow_queries', [])),
        'total_query_time': sum(q['duration'] for q in getattr(g, 'slow_queries', []))
    }
    return stats


def log_query_count():
    """
    Log the number of queries executed in the current request.
    This helps identify N+1 query problems.
    """
    if hasattr(g, 'query_count'):
        logger.info(f"Total queries executed in request: {g.query_count}")
    else:
        logger.debug("Query count not tracked for this request")


def enable_query_counting(app):
    """
    Enable query counting for the Flask app.
    
    Args:
        app: Flask application instance
    """
    @app.before_request
    def reset_query_count():
        """Reset query count at start of request"""
        g.query_count = 0
    
    @event.listens_for(Session, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Increment query count"""
        if hasattr(g, 'query_count'):
            g.query_count += 1

