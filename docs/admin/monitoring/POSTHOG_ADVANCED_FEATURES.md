# PostHog Advanced Features Guide

This guide explains how to leverage PostHog's advanced features in TimeTracker for better insights, experimentation, and feature management.

## 📊 What's Included

TimeTracker uses these PostHog-related analytics capabilities where configured:

1. **Person Properties** - Track user and installation characteristics
2. **Group Analytics** - Segment by version, platform, etc.
3. **Identify Calls** - Rich user profiles in PostHog
4. **Enhanced Event Properties** - Contextual data for better analysis
5. **Group Identification** - Cohort analysis by installation type

**Server-side feature gates** (rollouts, kill switches, route guards) are **not** implemented via PostHog in this codebase. Use environment variables and [`app/config.py`](../../../app/config.py) instead.

## 🎯 Person Properties

### For Users (Product Analytics)

When users log in, we automatically identify them with properties like:

```python
{
    "$set": {
        "role": "admin",
        "is_admin": true,
        "last_login": "2025-10-20T10:30:00",
        "auth_method": "oidc"
    },
    "$set_once": {
        "first_login": "2025-01-01T12:00:00",
        "signup_method": "local"
    }
}
```

**Benefits:**
- Segment users by role (admin vs regular user)
- Track user engagement over time
- Analyze behavior by auth method
- Build cohorts based on signup date

### For Installations (Telemetry)

Each installation is identified with properties like:

```python
{
    "$set": {
        "current_version": "3.0.0",
        "current_platform": "Linux",
        "environment": "production",
        "deployment_method": "docker",
        "auth_method": "oidc",
        "timezone": "Europe/Berlin",
        "last_seen": "2025-10-20 10:30:00"
    },
    "$set_once": {
        "first_seen_platform": "Linux",
        "first_seen_python_version": "3.12.0",
        "first_seen_version": "2.8.0"
    }
}
```

**Benefits:**
- Track version adoption and upgrade patterns
- Identify installations that need updates
- Segment by deployment method (Docker vs native)
- Geographic distribution via timezone

## 📦 Group Analytics

Installations are automatically grouped by:

### Version Groups
```python
{
    "group_type": "version",
    "group_key": "3.0.0",
    "properties": {
        "version_number": "3.0.0",
        "python_versions": ["3.12.0", "3.11.5"]
    }
}
```

### Platform Groups
```python
{
    "group_type": "platform",
    "group_key": "Linux",
    "properties": {
        "platform_name": "Linux",
        "platform_release": "5.15.0"
    }
}
```

**Use Cases:**
- "Show all events from installations running version 3.0.0"
- "How many Linux installations are active?"
- "Which Python versions are most common on Windows?"

## 🧪 Experiments and measurement

There is no in-app PostHog feature-flag or variant API. To compare behaviors, implement variants in your own code (for example driven by `app.config`) and **distinguish them in analytics** with explicit properties on `track_event` calls (see below).

### Track meaningful actions

```python
from app import track_event

track_event(
    user.id,
    "export.completed",
    {"export_type": "csv", "rows": 100, "experiment_variant": "b"},
)
```

## 📈 Enhanced Event Properties

All events now automatically include:

### User Events
- **Browser info**: `$browser`, `$device_type`, `$os`
- **Request context**: `$current_url`, `$pathname`, `$host`
- **Deployment info**: `environment`, `app_version`, `deployment_method`

### Telemetry Events
- **Platform details**: OS, release, machine type
- **Environment**: production/development/testing
- **Deployment**: Docker vs native
- **Auth method**: local vs OIDC
- **Timezone**: Installation timezone

## 🔍 Useful PostHog Queries

### Installation Analytics

**Active installations by version:**
```
Event: telemetry.health
Group by: version
Time range: Last 30 days
```

**New installations over time:**
```
Event: telemetry.install
Group by: Time
Breakdown: deployment_method
```

**Update adoption:**
```
Event: telemetry.update
Filter: old_version = "2.9.0"
Breakdown: new_version
```

### User Analytics

**Login methods:**
```
Event: auth.login
Breakdown: auth_method
```

**Feature usage by role:**
```
Event: project.created
Filter: Person property "role" = "admin"
```

**Timer usage patterns:**
```
Event: timer.started
Breakdown: Hour of day
```

## 🔐 Person Properties for Segmentation

### Available Person Properties

**Users:**
- `role` - User role (admin, user, etc.)
- `is_admin` - Boolean
- `auth_method` - local or oidc
- `signup_method` - How they signed up
- `first_login` - First login timestamp
- `last_login` - Most recent login

**Installations:**
- `current_version` - Current app version
- `current_platform` - Operating system
- `environment` - production/development
- `deployment_method` - docker/native
- `timezone` - Installation timezone
- `first_seen_version` - Original install version

### Creating Cohorts

**Example: Docker Users on Latest Version**
```
Person properties:
  deployment_method = "docker"
  current_version = "3.0.0"
```

**Example: Admins Using OIDC**
```
Person properties:
  is_admin = true
  auth_method = "oidc"
```

## 📊 Dashboard Examples

### Installation Health Dashboard

**Widgets:**
1. **Active Installations** - Count of `telemetry.health` last 24h
2. **Version Distribution** - Breakdown by `app_version`
3. **Platform Distribution** - Breakdown by `platform`
4. **Update Timeline** - `telemetry.update` events over time
5. **Error Rate** - Count of error events by version

### User Engagement Dashboard

**Widgets:**
1. **Daily Active Users** - Unique users per day
2. **Feature Usage** - Events by feature category
3. **Auth Method Split** - Pie chart of login methods
4. **Timer Usage** - `timer.started` events over time
5. **Export Activity** - `export.csv` events by user cohort

## 🚨 Kill switches and rollouts (application)

To disable or limit behavior for **all users** of an installation, use **configuration**: environment variables and [`app/config.py`](../../../app/config.py). That requires a deploy or config change, which is the supported model for this codebase.

## 🧑‍💻 Development best practices

### 1. Centralize deployment toggles

Add booleans or strings to `Config` in `app/config.py` and read them from the environment with safe defaults.

### 2. Default to safe values

Prefer secure or conservative defaults for production (for example registration off unless explicitly enabled).

### 3. Document env vars

When you add a new toggle, document the variable in deployment or admin docs so operators know how to set it.

### 4. Test behavior

Test both branches of a toggle in unit tests by patching `current_app.config` or the setting your view reads.

## 📚 Additional resources

- **PostHog Docs**: https://posthog.com/docs
- **Group Analytics**: https://posthog.com/docs/data/group-analytics
- **Person Properties**: https://posthog.com/docs/data/persons
- **Experiments**: https://posthog.com/docs/experiments

## 🎉 Benefits summary

With the analytics integration, you can:

✅ **Segment users** by role, auth method, platform, version  
✅ **Cohort analysis** to understand user behavior  
✅ **Track updates** and version adoption patterns  
✅ **Monitor health** of different installation types  
✅ **Identify trends** in feature usage  
✅ **Make data-driven decisions** about features  

---

**Last Updated:** 2025-10-20  
**Version:** 1.0  
**Status:** ✅ Production Ready
