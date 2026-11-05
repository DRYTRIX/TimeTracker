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

### Application toggles (server-side)

TimeTracker does **not** ship a PostHog-backed feature-flag API. Enable or restrict behavior with **environment variables** and [`app/config.py`](../../../app/config.py) (for example `DEMO_MODE`, `ALLOW_SELF_REGISTER`, `ENABLE_TELEMETRY`). Per-user UI options live on the user model in the database.

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

---

**Quick Tip:** Use person properties and cohorts in PostHog for analysis; gate behavior in the app with config and env vars.
