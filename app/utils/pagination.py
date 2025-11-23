"""
Pagination utilities for consistent pagination across the application.
"""

from typing import List, Any, Dict, Optional
from flask import request
from sqlalchemy.orm import Query
from app.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


def paginate_query(
    query: Query,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    max_per_page: int = MAX_PAGE_SIZE
) -> Dict[str, Any]:
    """
    Paginate a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        page: Page number (defaults to request arg or 1)
        per_page: Items per page (defaults to request arg or DEFAULT_PAGE_SIZE)
        max_per_page: Maximum items per page
        
    Returns:
        dict with 'items' and 'pagination' keys
    """
    # Get pagination parameters
    page = page or int(request.args.get('page', 1)) if request else 1
    per_page = per_page or int(request.args.get('per_page', DEFAULT_PAGE_SIZE)) if request else DEFAULT_PAGE_SIZE
    
    # Enforce maximum
    per_page = min(per_page, max_per_page)
    
    # Paginate
    paginated = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return {
        'items': paginated.items,
        'pagination': {
            'page': paginated.page,
            'per_page': paginated.per_page,
            'total': paginated.total,
            'pages': paginated.pages,
            'has_next': paginated.has_next,
            'has_prev': paginated.has_prev,
            'next_page': paginated.page + 1 if paginated.has_next else None,
            'prev_page': paginated.page - 1 if paginated.has_prev else None
        }
    }


def get_pagination_params(
    default_page: int = 1,
    default_per_page: int = DEFAULT_PAGE_SIZE,
    max_per_page: int = MAX_PAGE_SIZE
) -> tuple[int, int]:
    """
    Get pagination parameters from request.
    
    Returns:
        tuple of (page, per_page)
    """
    page = int(request.args.get('page', default_page)) if request else default_page
    per_page = int(request.args.get('per_page', default_per_page)) if request else default_per_page
    per_page = min(per_page, max_per_page)
    return page, per_page


def create_pagination_links(
    page: int,
    per_page: int,
    total: int,
    base_url: str
) -> Dict[str, Optional[str]]:
    """
    Create pagination links.
    
    Args:
        page: Current page
        per_page: Items per page
        total: Total items
        base_url: Base URL for links
        
    Returns:
        dict with pagination links
    """
    pages = (total + per_page - 1) // per_page if total > 0 else 0
    
    links = {
        'first': f"{base_url}?page=1&per_page={per_page}" if page > 1 else None,
        'last': f"{base_url}?page={pages}&per_page={per_page}" if pages > 0 and page < pages else None,
        'prev': f"{base_url}?page={page-1}&per_page={per_page}" if page > 1 else None,
        'next': f"{base_url}?page={page+1}&per_page={per_page}" if page < pages else None
    }
    
    return links

