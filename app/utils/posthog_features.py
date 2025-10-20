"""
PostHog Feature Flags and Advanced Features

This module provides utilities for using PostHog's advanced features:
- Feature flags (for A/B testing and gradual rollouts)
- Experiments
- Feature enablement checks
- Remote configuration
"""

import os
import posthog
from typing import Optional, Any, Dict
from functools import wraps
from flask import request


def is_posthog_enabled() -> bool:
    """Check if PostHog is enabled and configured"""
    return bool(os.getenv("POSTHOG_API_KEY", ""))


def get_feature_flag(user_id: Any, flag_key: str, default: bool = False) -> bool:
    """
    Check if a feature flag is enabled for a user.
    
    Args:
        user_id: The user ID (internal ID, not PII)
        flag_key: The feature flag key in PostHog
        default: Default value if PostHog is not configured
        
    Returns:
        True if feature is enabled, False otherwise
    """
    if not is_posthog_enabled():
        return default
    
    try:
        return posthog.feature_enabled(
            flag_key,
            str(user_id)
        ) or default
    except Exception:
        return default


def get_feature_flag_payload(user_id: Any, flag_key: str) -> Optional[Dict[str, Any]]:
    """
    Get the payload for a feature flag (for remote configuration).
    
    Example usage:
        config = get_feature_flag_payload(user.id, "new-dashboard-config")
        if config:
            theme = config.get("theme", "light")
            features = config.get("features", [])
    
    Args:
        user_id: The user ID
        flag_key: The feature flag key
        
    Returns:
        Dict with payload data, or None if not available
    """
    if not is_posthog_enabled():
        return None
    
    try:
        return posthog.get_feature_flag_payload(
            flag_key,
            str(user_id)
        )
    except Exception:
        return None


def get_all_feature_flags(user_id: Any) -> Dict[str, Any]:
    """
    Get all feature flags for a user.
    
    Returns a dictionary of flag_key -> enabled/disabled
    
    Args:
        user_id: The user ID
        
    Returns:
        Dict of feature flags
    """
    if not is_posthog_enabled():
        return {}
    
    try:
        return posthog.get_all_flags(str(user_id)) or {}
    except Exception:
        return {}


def feature_flag_required(flag_key: str, redirect_to: Optional[str] = None):
    """
    Decorator to require a feature flag for a route.
    
    Usage:
        @app.route('/beta-feature')
        @feature_flag_required('beta-features')
        def beta_feature():
            return "This is a beta feature!"
    
    Args:
        flag_key: The feature flag key to check
        redirect_to: URL to redirect to if flag is disabled (optional)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            from flask import abort, redirect, url_for
            
            if not current_user.is_authenticated:
                # Can't check feature flags for anonymous users
                if redirect_to:
                    return redirect(redirect_to)
                abort(403)
            
            if not get_feature_flag(current_user.id, flag_key):
                # Feature not enabled for this user
                if redirect_to:
                    return redirect(redirect_to)
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_active_experiments(user_id: Any) -> Dict[str, str]:
    """
    Get active experiments and their variants for a user.
    
    This can be used for A/B testing and tracking which
    variants users are seeing.
    
    Args:
        user_id: The user ID
        
    Returns:
        Dict of experiment_key -> variant
    """
    flags = get_all_feature_flags(user_id)
    
    # Filter for experiments (flags that have variants)
    experiments = {}
    for flag_key, value in flags.items():
        if isinstance(value, str) and value not in ["true", "false"]:
            # This is likely a multivariate flag (experiment)
            experiments[flag_key] = value
    
    return experiments


def inject_feature_flags_to_frontend(user_id: Any) -> Dict[str, Any]:
    """
    Get feature flags formatted for frontend injection.
    
    This can be used to inject feature flags into JavaScript
    for frontend feature toggling.
    
    Usage in template:
        <script>
            window.featureFlags = {{ feature_flags|tojson }};
        </script>
    
    Args:
        user_id: The user ID
        
    Returns:
        Dict of feature flags safe for frontend use
    """
    if not is_posthog_enabled():
        return {}
    
    try:
        flags = get_all_feature_flags(user_id)
        # Convert to boolean values for frontend
        return {
            key: bool(value) 
            for key, value in flags.items()
        }
    except Exception:
        return {}


def override_feature_flag(user_id: Any, flag_key: str, value: bool):
    """
    Override a feature flag for testing purposes.
    
    Note: This only works in development/testing environments.
    
    Args:
        user_id: The user ID
        flag_key: The feature flag key
        value: The value to set
    """
    if os.getenv("FLASK_ENV") not in ["development", "testing"]:
        # Only allow overrides in dev/test
        return
    
    try:
        # Store override in session or cache
        # This is a placeholder - implement based on your needs
        pass
    except Exception:
        pass


def track_feature_flag_interaction(user_id: Any, flag_key: str, action: str, properties: Optional[Dict] = None):
    """
    Track when users interact with features controlled by feature flags.
    
    This helps measure the impact of features and experiments.
    
    Args:
        user_id: The user ID
        flag_key: The feature flag key
        action: The action taken (e.g., "clicked", "viewed", "completed")
        properties: Additional properties to track
    """
    from app import track_event
    
    event_properties = {
        "feature_flag": flag_key,
        "action": action,
        **(properties or {})
    }
    
    track_event(user_id, "feature_interaction", event_properties)


# Predefined feature flags for common use cases
class FeatureFlags:
    """
    Centralized feature flag keys for the application.
    
    Define your feature flags here to avoid typos and enable autocomplete.
    """
    
    # Beta features
    BETA_FEATURES = "beta-features"
    NEW_DASHBOARD = "new-dashboard"
    ADVANCED_REPORTS = "advanced-reports"
    
    # Experiments
    TIMER_UI_EXPERIMENT = "timer-ui-experiment"
    ONBOARDING_FLOW = "onboarding-flow"
    
    # Rollout features
    NEW_ANALYTICS_PAGE = "new-analytics-page"
    BULK_OPERATIONS = "bulk-operations"
    
    # Kill switches (for emergency feature disabling)
    ENABLE_EXPORTS = "enable-exports"
    ENABLE_API = "enable-api"
    ENABLE_WEBSOCKETS = "enable-websockets"
    
    # Premium features (if you have paid tiers)
    CUSTOM_REPORTS = "custom-reports"
    API_ACCESS = "api-access"
    INTEGRATIONS = "integrations"


# Example usage helper
def is_feature_enabled_for_request(flag_key: str, default: bool = False) -> bool:
    """
    Check if a feature is enabled for the current request's user.
    
    Convenience function for use in templates and view functions.
    
    Args:
        flag_key: The feature flag key
        default: Default value if user not authenticated
        
    Returns:
        True if feature is enabled
    """
    from flask_login import current_user
    
    if not current_user.is_authenticated:
        return default
    
    return get_feature_flag(current_user.id, flag_key, default)

