"""
PostHog Segmentation Utilities

Advanced user segmentation and identification with computed properties.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import os


def is_segmentation_enabled() -> bool:
    """Check if PostHog segmentation is enabled."""
    return bool(os.getenv("POSTHOG_API_KEY", ""))


def identify_user_with_segments(user_id: Any, user) -> None:
    """
    Identify user with comprehensive segmentation properties.
    
    This sets person properties in PostHog that can be used for:
    - Creating cohorts
    - Targeting feature flags
    - Analyzing behavior by segment
    - A/B testing
    
    Args:
        user_id: User ID
        user: User model instance
    """
    if not is_segmentation_enabled():
        return
    
    from app import identify_user
    from app.models import TimeEntry, Project
    
    # Calculate engagement metrics
    engagement_metrics = calculate_engagement_metrics(user_id)
    
    # Calculate usage patterns
    usage_patterns = calculate_usage_patterns(user_id)
    
    # Get account info
    account_info = get_account_info(user)
    
    # Combine all properties
    properties = {
        "$set": {
            # User role and permissions
            "role": user.role,
            "is_admin": user.is_admin,
            
            # Authentication
            "auth_method": getattr(user, 'auth_method', 'local'),
            
            # Engagement metrics
            **engagement_metrics,
            
            # Usage patterns
            **usage_patterns,
            
            # Account info
            **account_info,
            
            # Last updated
            "last_segment_update": datetime.utcnow().isoformat(),
        },
        "$set_once": {
            "first_login": user.created_at.isoformat() if user.created_at else None,
            "signup_method": "local",  # Or from user object if tracked
        }
    }
    
    identify_user(user_id, properties)


def calculate_engagement_metrics(user_id: Any) -> Dict[str, Any]:
    """
    Calculate user engagement metrics.
    
    Returns:
        Dict of engagement properties
    """
    from app.models import TimeEntry
    
    now = datetime.utcnow()
    
    # Entries in different time periods
    entries_last_24h = TimeEntry.query.filter(
        TimeEntry.user_id == user_id,
        TimeEntry.created_at >= now - timedelta(hours=24)
    ).count()
    
    entries_last_7_days = TimeEntry.query.filter(
        TimeEntry.user_id == user_id,
        TimeEntry.created_at >= now - timedelta(days=7)
    ).count()
    
    entries_last_30_days = TimeEntry.query.filter(
        TimeEntry.user_id == user_id,
        TimeEntry.created_at >= now - timedelta(days=30)
    ).count()
    
    entries_all_time = TimeEntry.query.filter(
        TimeEntry.user_id == user_id
    ).count()
    
    # Calculate engagement level
    if entries_last_7_days >= 20:
        engagement_level = "very_high"
    elif entries_last_7_days >= 10:
        engagement_level = "high"
    elif entries_last_7_days >= 3:
        engagement_level = "medium"
    elif entries_last_7_days >= 1:
        engagement_level = "low"
    else:
        engagement_level = "inactive"
    
    # Calculate activity trend
    if entries_last_7_days > entries_last_30_days / 4:
        activity_trend = "increasing"
    elif entries_last_7_days < entries_last_30_days / 5:
        activity_trend = "decreasing"
    else:
        activity_trend = "stable"
    
    return {
        "entries_last_24h": entries_last_24h,
        "entries_last_7_days": entries_last_7_days,
        "entries_last_30_days": entries_last_30_days,
        "entries_all_time": entries_all_time,
        "engagement_level": engagement_level,
        "activity_trend": activity_trend,
        "is_active_user": entries_last_7_days > 0,
        "is_power_user": entries_last_7_days >= 10,
        "is_at_risk": entries_last_7_days == 0 and entries_all_time > 0,
    }


def calculate_usage_patterns(user_id: Any) -> Dict[str, Any]:
    """
    Calculate user usage patterns.
    
    Returns:
        Dict of usage pattern properties
    """
    from app.models import Project, TimeEntry, Task
    from sqlalchemy import func
    
    # Project statistics
    active_projects = Project.query.filter_by(
        status='active'
    ).filter(
        Project.time_entries.any(TimeEntry.user_id == user_id)
    ).count()
    
    total_projects = Project.query.filter(
        Project.time_entries.any(TimeEntry.user_id == user_id)
    ).count()
    
    # Task statistics (if tasks exist)
    try:
        assigned_tasks = Task.query.filter_by(
            assigned_to=user_id,
            status__ne='done'
        ).count()
        
        completed_tasks = Task.query.filter_by(
            assigned_to=user_id,
            status='done'
        ).count()
    except Exception:
        assigned_tasks = 0
        completed_tasks = 0
    
    # Timer usage
    timer_entries = TimeEntry.query.filter(
        TimeEntry.user_id == user_id,
        TimeEntry.source == 'timer'
    ).count()
    
    manual_entries = TimeEntry.query.filter(
        TimeEntry.user_id == user_id,
        TimeEntry.source == 'manual'
    ).count()
    
    total_entries = timer_entries + manual_entries
    timer_usage_percent = (timer_entries / total_entries * 100) if total_entries > 0 else 0
    
    # Preferred tracking method
    if timer_usage_percent > 70:
        preferred_method = "timer"
    elif timer_usage_percent > 30:
        preferred_method = "mixed"
    else:
        preferred_method = "manual"
    
    # Calculate total hours tracked
    total_seconds = TimeEntry.query.filter(
        TimeEntry.user_id == user_id,
        TimeEntry.duration_seconds.isnot(None)
    ).with_entities(
        func.sum(TimeEntry.duration_seconds)
    ).scalar() or 0
    
    total_hours = round(total_seconds / 3600, 1)
    
    return {
        "active_projects_count": active_projects,
        "total_projects_count": total_projects,
        "assigned_tasks_count": assigned_tasks,
        "completed_tasks_count": completed_tasks,
        "timer_entries_count": timer_entries,
        "manual_entries_count": manual_entries,
        "timer_usage_percent": round(timer_usage_percent, 1),
        "preferred_tracking_method": preferred_method,
        "total_hours_tracked": total_hours,
        "uses_timer": timer_entries > 0,
        "uses_manual_entry": manual_entries > 0,
    }


def get_account_info(user) -> Dict[str, Any]:
    """
    Get account information.
    
    Returns:
        Dict of account properties
    """
    from datetime import datetime
    
    account_age_days = (datetime.utcnow() - user.created_at).days if user.created_at else 0
    
    # Categorize by account age
    if account_age_days < 7:
        account_age_category = "new"
    elif account_age_days < 30:
        account_age_category = "recent"
    elif account_age_days < 180:
        account_age_category = "established"
    else:
        account_age_category = "long_term"
    
    # Days since last login
    days_since_login = (datetime.utcnow() - user.last_login).days if user.last_login else None
    
    return {
        "account_age_days": account_age_days,
        "account_age_category": account_age_category,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "days_since_last_login": days_since_login,
        "username": None,  # Never send PII
        "is_new_user": account_age_days < 7,
        "is_established_user": account_age_days >= 30,
    }


# ============================================================================
# Cohort Definitions
# ============================================================================

class UserCohorts:
    """
    Predefined user cohort definitions for PostHog.
    
    Use these in PostHog to create cohorts:
    Person Properties → engagement_level = "high"
    """
    
    # Engagement cohorts
    VERY_HIGH_ENGAGEMENT = {"engagement_level": "very_high"}
    HIGH_ENGAGEMENT = {"engagement_level": "high"}
    MEDIUM_ENGAGEMENT = {"engagement_level": "medium"}
    LOW_ENGAGEMENT = {"engagement_level": "low"}
    INACTIVE = {"engagement_level": "inactive"}
    
    # Activity cohorts
    POWER_USERS = {"is_power_user": True}
    ACTIVE_USERS = {"is_active_user": True}
    AT_RISK_USERS = {"is_at_risk": True}
    
    # Usage pattern cohorts
    TIMER_USERS = {"preferred_tracking_method": "timer"}
    MANUAL_ENTRY_USERS = {"preferred_tracking_method": "manual"}
    MIXED_METHOD_USERS = {"preferred_tracking_method": "mixed"}
    
    # Account age cohorts
    NEW_USERS = {"account_age_category": "new"}
    RECENT_USERS = {"account_age_category": "recent"}
    ESTABLISHED_USERS = {"account_age_category": "established"}
    LONG_TERM_USERS = {"account_age_category": "long_term"}
    
    # Role cohorts
    ADMINS = {"is_admin": True}
    REGULAR_USERS = {"is_admin": False}
    
    # Activity trend cohorts
    GROWING_USERS = {"activity_trend": "increasing"}
    DECLINING_USERS = {"activity_trend": "decreasing"}
    STABLE_USERS = {"activity_trend": "stable"}


def get_user_cohort_description(user_properties: Dict[str, Any]) -> str:
    """
    Get a human-readable description of a user's cohort.
    
    Args:
        user_properties: User properties from PostHog
        
    Returns:
        String describing the user's primary cohort
    """
    engagement = user_properties.get("engagement_level", "unknown")
    is_admin = user_properties.get("is_admin", False)
    account_age = user_properties.get("account_age_category", "unknown")
    
    if is_admin:
        return f"Admin user with {engagement} engagement"
    
    return f"{account_age.title()} user with {engagement} engagement"


# ============================================================================
# Super Properties
# ============================================================================

def set_super_properties(user_id: Any, user) -> None:
    """
    Set super properties that are included in every event.
    
    These properties are automatically added to all events without
    needing to pass them explicitly.
    
    Args:
        user_id: User ID
        user: User model instance
    """
    if not is_segmentation_enabled():
        return
    
    from app import identify_user
    
    properties = {
        "$set": {
            # Always include these in events
            "role": user.role,
            "is_admin": user.is_admin,
            "auth_method": getattr(user, 'auth_method', 'local'),
            "timezone": os.getenv('TZ', 'UTC'),
            "environment": os.getenv('FLASK_ENV', 'production'),
            "deployment_method": "docker" if os.path.exists("/.dockerenv") else "native",
        }
    }
    
    identify_user(user_id, properties)


# ============================================================================
# Segment Updates
# ============================================================================

def should_update_segments(user_id: Any) -> bool:
    """
    Check if user segments should be updated.
    
    Updates segments if:
    - Never updated before
    - Last updated > 24 hours ago
    - Significant activity since last update
    
    Returns:
        True if segments should be updated
    """
    # For now, always return True
    # In production, you might want to cache this and check timestamps
    return True


def update_user_segments_if_needed(user_id: Any, user) -> None:
    """
    Update user segments if needed.
    
    Call this periodically (e.g., on login, after significant actions).
    
    Args:
        user_id: User ID
        user: User model instance
    """
    if should_update_segments(user_id):
        identify_user_with_segments(user_id, user)

