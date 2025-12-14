# PostHog Quick Reference Card

## 🚀 Quick Start

```bash
# Enable PostHog
POSTHOG_API_KEY=your-api-key
POSTHOG_HOST=https://app.posthog.com

# Enable telemetry (uses PostHog)
ENABLE_TELEMETRY=true
```

## 🔍 Common Tasks

### Track an Event
```python
from app import track_event

track_event(user.id, "feature.used", {
    "feature_name": "export",
    "format": "csv"
})
```

### Identify a User
```python
from app import identify_user

identify_user(user.id, {
    "$set": {
        "role": "admin",
        "plan": "pro"
    },
    "$set_once": {
        "signup_date": "2025-01-01"
    }
})
```

### Check Feature Flag
```python
from app.utils.posthog_features import get_feature_flag

if get_feature_flag(user.id, "new-feature"):
    # Enable feature
    pass
```

### Protect Route with Flag
```python
from app.utils.posthog_features import feature_flag_required

@app.route('/beta/feature')
@feature_flag_required('beta-access')
def beta_feature():
    return "Beta!"
```

### Get Flag Payload (Remote Config)
```python
from app.utils.posthog_features import get_feature_flag_payload

config = get_feature_flag_payload(user.id, "app-config")
if config:
    theme = config.get("theme", "light")
```

### Inject Flags to Frontend
```python
from app.utils.posthog_features import inject_feature_flags_to_frontend

@app.route('/dashboard')
def dashboard():
    flags = inject_feature_flags_to_frontend(current_user.id)
    return render_template("dashboard.html", feature_flags=flags)
```

```html
<script>
    window.featureFlags = {{ feature_flags|tojson }};
</script>
```

## 📊 Person Properties

### Automatically Set on Login
- `role` - User role
- `is_admin` - Admin status
- `auth_method` - local or oidc
- `last_login` - Last login timestamp
- `first_login` - First login (set once)
- `signup_method` - How they signed up (set once)

### Automatically Set for Installations
- `current_version` - App version
- `current_platform` - OS (Linux, Windows, etc.)
- `environment` - production/development
- `deployment_method` - docker/native
- `timezone` - Installation timezone
- `first_seen_version` - Original version (set once)

## 🎯 Feature Flag Examples

### Gradual Rollout
```
Key: new-ui
Rollout: 10% → 25% → 50% → 100%
```

### Target Admins Only
```
Key: admin-tools
Condition: is_admin = true
```

### Platform Specific
```
Key: linux-optimizations
Condition: current_platform = "Linux"
```

### Version Specific
```
Key: v3-features
Condition: current_version >= "3.0.0"
```

### Kill Switch
```
Key: enable-exports
Default: true
Use in code: default=True
```

## 📈 Useful PostHog Queries

### Active Users by Role
```
Event: auth.login
Breakdown: role
Time: Last 30 days
```

### Feature Usage
```
Event: feature_interaction
Breakdown: feature_flag
Filter: action = "clicked"
```

### Version Distribution
```
Event: telemetry.health
Breakdown: app_version
Time: Last 7 days
```

### Update Adoption
```
Event: telemetry.update
Filter: new_version = "3.0.0"
Time: Last 90 days
Cumulative: Yes
```

### Platform Comparison
```
Event: timer.started
Breakdown: platform
Compare: All platforms
```

## 🔐 Privacy Guidelines

**✅ DO:**
- Use internal user IDs
- Track feature usage
- Set role/admin properties
- Use anonymous fingerprints for telemetry

**❌ DON'T:**
- Send usernames or emails
- Include project names
- Track sensitive business data
- Send any PII

## 🧪 Testing

### Mock Feature Flags
```python
from unittest.mock import patch

def test_with_feature_enabled():
    with patch('app.utils.posthog_features.get_feature_flag', return_value=True):
        # Test with feature enabled
        pass
```

### Mock Track Events
```python
@patch('app.track_event')
def test_event_tracking(mock_track):
    # Do something that tracks an event
    mock_track.assert_called_once_with(user.id, "event.name", {...})
```

## 📚 More Information

- **Full Guide**: [POSTHOG_ADVANCED_FEATURES.md](POSTHOG_ADVANCED_FEATURES.md)
- **Implementation**: [POSTHOG_ENHANCEMENTS_SUMMARY.md](POSTHOG_ENHANCEMENTS_SUMMARY.md)
- **Analytics Docs**: [docs/analytics.md](docs/analytics.md)
- **PostHog Docs**: https://posthog.com/docs

## 🎯 Predefined Feature Flags

```python
from app.utils.posthog_features import FeatureFlags

# Beta features
FeatureFlags.BETA_FEATURES
FeatureFlags.NEW_DASHBOARD
FeatureFlags.ADVANCED_REPORTS

# Experiments
FeatureFlags.TIMER_UI_EXPERIMENT
FeatureFlags.ONBOARDING_FLOW

# Rollouts
FeatureFlags.NEW_ANALYTICS_PAGE
FeatureFlags.BULK_OPERATIONS

# Kill switches
FeatureFlags.ENABLE_EXPORTS
FeatureFlags.ENABLE_API
FeatureFlags.ENABLE_WEBSOCKETS

# Premium
FeatureFlags.CUSTOM_REPORTS
FeatureFlags.API_ACCESS
FeatureFlags.INTEGRATIONS
```

---

**Quick Tip:** Start with small rollouts (10%) and gradually increase as you gain confidence!

