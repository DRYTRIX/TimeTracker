# PostHog Advanced Features Guide

This guide explains how to leverage PostHog's advanced features in TimeTracker for better insights, experimentation, and feature management.

## 📊 What's Included

TimeTracker now uses these PostHog features:

1. **Person Properties** - Track user and installation characteristics
2. **Group Analytics** - Segment by version, platform, etc.
3. **Feature Flags** - Gradual rollouts and A/B testing
4. **Identify Calls** - Rich user profiles in PostHog
5. **Enhanced Event Properties** - Contextual data for better analysis
6. **Group Identification** - Cohort analysis by installation type

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

## 🚀 Feature Flags

### Basic Usage

Check if a feature is enabled:

```python
from app.utils.posthog_features import get_feature_flag

if get_feature_flag(user.id, "new-dashboard"):
    return render_template("dashboard_v2.html")
else:
    return render_template("dashboard.html")
```

### Route Protection

Require a feature flag for entire routes:

```python
from app.utils.posthog_features import feature_flag_required

@app.route('/beta/advanced-analytics')
@feature_flag_required('beta-features')
def advanced_analytics():
    return render_template("analytics_beta.html")
```

### Remote Configuration

Use feature flag payloads for configuration:

```python
from app.utils.posthog_features import get_feature_flag_payload

config = get_feature_flag_payload(user.id, "dashboard-config")
if config:
    theme = config.get("theme", "light")
    widgets = config.get("enabled_widgets", [])
```

### Frontend Feature Flags

Inject flags into JavaScript:

```python
# In your view function
from app.utils.posthog_features import inject_feature_flags_to_frontend

@app.route('/dashboard')
def dashboard():
    feature_flags = inject_feature_flags_to_frontend(current_user.id)
    return render_template("dashboard.html", feature_flags=feature_flags)
```

```html
<!-- In your template -->
<script>
    window.featureFlags = {{ feature_flags|tojson }};
    
    if (window.featureFlags['new-timer-ui']) {
        // Load new timer UI
    }
</script>
```

### Predefined Feature Flags

Use the `FeatureFlags` class to avoid typos:

```python
from app.utils.posthog_features import FeatureFlags

if get_feature_flag(user.id, FeatureFlags.ADVANCED_REPORTS):
    # Enable advanced reports
    pass
```

## 🧪 A/B Testing & Experiments

### Track Experiment Variants

```python
from app.utils.posthog_features import get_active_experiments

experiments = get_active_experiments(user.id)
# {"timer-ui-experiment": "variant-b"}

if experiments.get("timer-ui-experiment") == "variant-b":
    # Show variant B
    pass
```

### Track Feature Interactions

```python
from app.utils.posthog_features import track_feature_flag_interaction

track_feature_flag_interaction(
    user.id,
    "new-dashboard",
    "clicked_export_button",
    {"export_type": "csv", "rows": 100}
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

## 🎨 Setting Up Feature Flags in PostHog

### 1. Create a Feature Flag

1. Go to PostHog → Feature Flags
2. Click "New feature flag"
3. Set key (e.g., `new-dashboard`)
4. Configure rollout:
   - **Boolean**: On/off for everyone
   - **Percentage**: Gradual rollout (e.g., 10% of users)
   - **Person properties**: Target specific users
   - **Groups**: Target specific platforms/versions

### 2. Target Specific Users

**Example: Enable for admins only**
```
Match person properties:
  is_admin = true
```

**Example: Enable for Docker installations**
```
Match group properties:
  deployment_method = "docker"
```

### 3. Gradual Rollout

1. Start at 0% (disabled)
2. Roll out to 10% (testing)
3. Increase to 50% (beta)
4. Increase to 100% (full release)
5. Remove flag from code

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

## 🚨 Kill Switches

Use feature flags as emergency kill switches:

```python
from app.utils.posthog_features import get_feature_flag, FeatureFlags

@app.route('/api/export')
def api_export():
    if not get_feature_flag(current_user.id, FeatureFlags.ENABLE_EXPORTS, default=True):
        abort(503, "Exports temporarily disabled")
    
    # Proceed with export
```

**Benefits:**
- Instantly disable problematic features
- No deployment needed
- Can target specific user segments
- Helps during incidents

## 🧑‍💻 Development Best Practices

### 1. Define Flags Centrally

```python
# In app/utils/posthog_features.py
class FeatureFlags:
    MY_NEW_FEATURE = "my-new-feature"
```

### 2. Default to Safe Values

```python
# Default to False for new features
if get_feature_flag(user.id, "risky-feature", default=False):
    # Enable risky feature
```

### 3. Clean Up Old Flags

Once a feature is fully rolled out:
1. Remove the flag check from code
2. Delete the flag in PostHog
3. Document in release notes

### 4. Test Flag Behavior

```python
def test_feature_flag():
    with mock.patch('app.utils.posthog_features.get_feature_flag') as mock_flag:
        mock_flag.return_value = True
        # Test with flag enabled
        
        mock_flag.return_value = False
        # Test with flag disabled
```

## 📚 Additional Resources

- **PostHog Docs**: https://posthog.com/docs
- **Feature Flags**: https://posthog.com/docs/feature-flags
- **Group Analytics**: https://posthog.com/docs/data/group-analytics
- **Person Properties**: https://posthog.com/docs/data/persons
- **Experiments**: https://posthog.com/docs/experiments

## 🎉 Benefits Summary

Using these PostHog features, you can now:

✅ **Segment users** by role, auth method, platform, version  
✅ **Gradually roll out** features to test with small groups  
✅ **A/B test** different UI variations  
✅ **Kill switches** for emergency feature disabling  
✅ **Remote config** without deploying code changes  
✅ **Cohort analysis** to understand user behavior  
✅ **Track updates** and version adoption patterns  
✅ **Monitor health** of different installation types  
✅ **Identify trends** in feature usage  
✅ **Make data-driven decisions** about features  

---

**Last Updated:** 2025-10-20  
**Version:** 1.0  
**Status:** ✅ Production Ready

