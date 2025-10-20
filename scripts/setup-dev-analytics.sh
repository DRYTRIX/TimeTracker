#!/bin/bash
# Setup script for local development with analytics

set -e

echo "🔧 TimeTracker Development Analytics Setup"
echo ""

# Check if .gitignore already has the entry
if ! grep -q "analytics_defaults_local.py" .gitignore 2>/dev/null; then
    echo "app/config/analytics_defaults_local.py" >> .gitignore
    echo "✅ Added analytics_defaults_local.py to .gitignore"
fi

# Check if local config already exists
if [ -f "app/config/analytics_defaults_local.py" ]; then
    echo "⚠️  Local config already exists"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing config"
        exit 0
    fi
fi

# Prompt for keys
echo ""
echo "📝 Enter your development analytics keys:"
echo "(Leave empty to skip)"
echo ""

read -p "PostHog API Key (starts with phc_): " POSTHOG_KEY
read -p "PostHog Host [https://app.posthog.com]: " POSTHOG_HOST
POSTHOG_HOST=${POSTHOG_HOST:-https://app.posthog.com}

read -p "Sentry DSN (optional): " SENTRY_DSN
read -p "Sentry Traces Rate [1.0]: " SENTRY_RATE
SENTRY_RATE=${SENTRY_RATE:-1.0}

# Create local config file
cat > app/config/analytics_defaults_local.py <<EOF
"""
Local development analytics configuration.

⚠️  DO NOT COMMIT THIS FILE ⚠️

This file is gitignored and contains your development API keys.
"""

# PostHog Configuration (Development)
POSTHOG_API_KEY_DEFAULT = "${POSTHOG_KEY}"
POSTHOG_HOST_DEFAULT = "${POSTHOG_HOST}"

# Sentry Configuration (Development)
SENTRY_DSN_DEFAULT = "${SENTRY_DSN}"
SENTRY_TRACES_RATE_DEFAULT = "${SENTRY_RATE}"


def _get_version_from_setup():
    """
    Get the application version from setup.py.
    
    This is the authoritative source for version information.
    Reads setup.py at runtime to get the current version.
    
    Returns:
        str: Application version (e.g., "3.0.0")
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
        version_match = re.search(r'version\s*=\s*[\'"]([^\'"]+)[\'"]', content)
        
        if version_match:
            return version_match.group(1)
    except Exception:
        pass
    
    # Fallback version if setup.py can't be read
    return "3.0.0-dev"


def get_analytics_config():
    """Get analytics configuration for local development."""
    
    # App version - read from setup.py at runtime
    app_version = _get_version_from_setup()
    
    return {
        "posthog_api_key": POSTHOG_API_KEY_DEFAULT,
        "posthog_host": POSTHOG_HOST_DEFAULT,
        "sentry_dsn": SENTRY_DSN_DEFAULT,
        "sentry_traces_rate": float(SENTRY_TRACES_RATE_DEFAULT),
        "app_version": app_version,
        "telemetry_enabled_default": False,
    }


def has_analytics_configured():
    """Check if analytics keys are configured."""
    return bool(POSTHOG_API_KEY_DEFAULT)
EOF

echo ""
echo "✅ Created app/config/analytics_defaults_local.py"

# Update __init__.py if not already done
if ! grep -q "analytics_defaults_local" app/config/__init__.py 2>/dev/null; then
    echo ""
    echo "📝 Updating app/config/__init__.py..."
    
    # Backup original
    cp app/config/__init__.py app/config/__init__.py.backup
    
    # Create new version with local import
    cat > app/config/__init__.py <<'EOF'
"""
Configuration module for TimeTracker.

This module contains analytics configuration that is embedded at build time
to enable consistent telemetry collection across all installations.

For local development, it tries to import from analytics_defaults_local.py first.
"""

# Try to import local development config first, fallback to production config
try:
    from app.config.analytics_defaults_local import get_analytics_config, has_analytics_configured
    print("📊 Using local analytics configuration for development")
except ImportError:
    from app.config.analytics_defaults import get_analytics_config, has_analytics_configured

__all__ = ['get_analytics_config', 'has_analytics_configured']
EOF
    
    echo "✅ Updated app/config/__init__.py to use local config"
    echo "   (Backup saved as __init__.py.backup)"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start the application: docker-compose up -d"
echo "2. Access: http://localhost:5000"
echo "3. Complete setup and enable telemetry"
echo "4. Check PostHog dashboard for events"
echo ""
echo "⚠️  Remember:"
echo "- This config is gitignored and won't be committed"
echo "- Use a separate PostHog project for development"
echo "- Before committing, ensure no keys in analytics_defaults.py"
echo ""
echo "To revert changes:"
echo "  rm app/config/analytics_defaults_local.py"
echo "  mv app/config/__init__.py.backup app/config/__init__.py"
echo ""

