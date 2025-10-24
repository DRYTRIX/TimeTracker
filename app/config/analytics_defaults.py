"""
Analytics configuration for TimeTracker.

These values are embedded at build time and cannot be overridden by users.
This allows collecting anonymized usage metrics from all installations
to improve the product while respecting user privacy.

Key Privacy Protections:
- Telemetry is OPT-IN (disabled by default)
- No personally identifiable information is ever collected
- Users can disable telemetry at any time via admin dashboard
- All tracked events are documented and transparent

DO NOT commit actual keys to this file - they are injected at build time only.
"""

# PostHog Configuration
# Replaced by GitHub Actions: POSTHOG_API_KEY_PLACEHOLDER
POSTHOG_API_KEY_DEFAULT = "%%POSTHOG_API_KEY_PLACEHOLDER%%"
POSTHOG_HOST_DEFAULT = "https://us.i.posthog.com"

# Sentry Configuration
# Replaced by GitHub Actions: SENTRY_DSN_PLACEHOLDER
SENTRY_DSN_DEFAULT = "%%SENTRY_DSN_PLACEHOLDER%%"
SENTRY_TRACES_RATE_DEFAULT = "0.1"

# Telemetry Configuration
# All builds have analytics configured, but telemetry is OPT-IN
TELE_ENABLED_DEFAULT = "false"  # Disabled by default for privacy

def _get_version_from_setup():
    """
    Get the application version from setup.py.
    
    setup.py is the SINGLE SOURCE OF TRUTH for version information.
    This function reads setup.py at runtime to get the current version.
    All other code should reference this function, not define versions themselves.
    
    Returns:
        str: Application version (e.g., "3.1.0") or "unknown" if setup.py can't be read
    """
    import os
    import re
    
    try:
        # Get path to setup.py (root of project)
        setup_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'setup.py')
        
        # Read setup.py
        with open(setup_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract version using regex
        # Matches: version='X.Y.Z' or version="X.Y.Z"
        version_match = re.search(r'version\s*=\s*[\'"]([^\'"]+)[\'"]', content)
        
        if version_match:
            return version_match.group(1)
    except Exception:
        pass
    
    # Fallback version if setup.py can't be read
    # This is the ONLY place besides setup.py where version is defined
    return "unknown"


def get_analytics_config():
    """
    Get analytics configuration.
    
    Analytics keys are embedded at build time and cannot be overridden
    to ensure consistent telemetry collection across all installations.
    
    However, users maintain full control:
    - Telemetry is OPT-IN (disabled by default)
    - Can be disabled anytime in admin dashboard
    - No PII is ever collected
    
    Returns:
        dict: Analytics configuration
    """
    # Helper to check if a value is a placeholder (not replaced by GitHub Actions)
    def is_placeholder(value):
        return value.startswith("%%") and value.endswith("%%")
    
    # PostHog configuration - use embedded keys (no override)
    posthog_api_key = POSTHOG_API_KEY_DEFAULT if not is_placeholder(POSTHOG_API_KEY_DEFAULT) else ""
    
    # Sentry configuration - use embedded keys (no override)
    sentry_dsn = SENTRY_DSN_DEFAULT if not is_placeholder(SENTRY_DSN_DEFAULT) else ""
    
    # App version - read from setup.py at runtime
    app_version = _get_version_from_setup()
    
    # Note: Environment variables are NOT checked for keys to prevent override
    # Users control telemetry via the opt-in/opt-out toggle in admin dashboard
    
    return {
        "posthog_api_key": posthog_api_key,
        "posthog_host": POSTHOG_HOST_DEFAULT,  # Fixed host, no override
        "sentry_dsn": sentry_dsn,
        "sentry_traces_rate": float(SENTRY_TRACES_RATE_DEFAULT),  # Fixed rate, no override
        "app_version": app_version,
        "telemetry_enabled_default": False,  # Always opt-in
    }


def has_analytics_configured():
    """
    Check if analytics keys are configured (embedded at build time).
    
    Returns:
        bool: True if analytics keys are embedded
    """
    def is_placeholder(value):
        return value.startswith("%%") and value.endswith("%%")
    
    # Check if keys have been replaced during build
    return not is_placeholder(POSTHOG_API_KEY_DEFAULT)
