# Time Rounding Preferences - Per-User Settings

## Overview

The Time Rounding Preferences feature allows each user to configure how their time entries are rounded when they stop timers. This provides flexibility for different billing practices and time tracking requirements while maintaining accurate time records.

## Key Features

- **Per-User Configuration**: Each user can set their own rounding preferences independently
- **Multiple Rounding Intervals**: Support for 1, 5, 10, 15, 30, and 60-minute intervals
- **Three Rounding Methods**:
  - **Nearest**: Round to the closest interval (standard rounding)
  - **Up**: Always round up to the next interval (ceiling)
  - **Down**: Always round down to the previous interval (floor)
- **Enable/Disable Toggle**: Users can disable rounding to track exact time
- **Real-time Preview**: Visual examples show how rounding will be applied

## User Guide

### Accessing Rounding Settings

1. Navigate to **Settings** from the user menu
2. Scroll to the **Time Rounding Preferences** section
3. Configure your preferences:
   - Toggle **Enable Time Rounding** on/off
   - Select your preferred **Rounding Interval**
   - Choose your **Rounding Method**
4. Click **Save Settings** to apply changes

### Understanding Rounding Methods

#### Round to Nearest (Default)
Standard mathematical rounding to the closest interval.

**Example** with 15-minute intervals:
- 7 minutes → 0 minutes
- 8 minutes → 15 minutes
- 62 minutes → 60 minutes
- 68 minutes → 75 minutes

#### Always Round Up
Always rounds up to the next interval, ensuring you never under-bill.

**Example** with 15-minute intervals:
- 1 minute → 15 minutes
- 61 minutes → 75 minutes
- 60 minutes → 60 minutes (exact match)

#### Always Round Down
Always rounds down to the previous interval, ensuring conservative billing.

**Example** with 15-minute intervals:
- 14 minutes → 0 minutes
- 74 minutes → 60 minutes
- 75 minutes → 75 minutes (exact match)

### Choosing the Right Settings

**For Freelancers/Contractors:**
- Use **15-minute intervals** with **Round to Nearest** for balanced billing
- Use **Round Up** if client agreements favor rounding up
- Use **5 or 10 minutes** for more granular tracking

**For Internal Time Tracking:**
- Use **No rounding (1 minute)** for exact time tracking
- Use **15 or 30 minutes** for simplified reporting

**For Project-Based Billing:**
- Use **30 or 60 minutes** for project-level granularity
- Use **Round Down** for conservative estimates

## Technical Details

### Database Schema

The following fields are added to the `users` table:

```sql
time_rounding_enabled BOOLEAN DEFAULT 1 NOT NULL
time_rounding_minutes INTEGER DEFAULT 1 NOT NULL
time_rounding_method VARCHAR(10) DEFAULT 'nearest' NOT NULL
```

### Default Values

For new and existing users:
- **Enabled**: `True` (rounding is enabled by default)
- **Minutes**: `1` (no rounding, exact time)
- **Method**: `'nearest'` (standard rounding)

### How Rounding is Applied

1. **Timer Start**: When a user starts a timer, no rounding is applied
2. **Timer Stop**: When a user stops a timer:
   - Calculate raw duration (end time - start time)
   - Apply user's rounding preferences
   - Store rounded duration in `duration_seconds` field
3. **Manual Entries**: Rounding is applied when creating/editing manual entries

### Backward Compatibility

The feature is fully backward compatible:
- If user preferences don't exist, the system falls back to the global `ROUNDING_MINUTES` config setting
- Existing time entries are not retroactively rounded
- Users without the new fields will use global rounding settings

## API Integration

### Get User Rounding Settings

```python
from app.utils.time_rounding import get_user_rounding_settings

settings = get_user_rounding_settings(user)
# Returns: {'enabled': True, 'minutes': 15, 'method': 'nearest'}
```

### Apply Rounding to Duration

```python
from app.utils.time_rounding import apply_user_rounding

raw_seconds = 3720  # 62 minutes
rounded_seconds = apply_user_rounding(raw_seconds, user)
# Returns: 3600 (60 minutes) with 15-min nearest rounding
```

### Manual Rounding

```python
from app.utils.time_rounding import round_time_duration

rounded = round_time_duration(
    duration_seconds=3720,  # 62 minutes
    rounding_minutes=15,
    rounding_method='up'
)
# Returns: 4500 (75 minutes)
```

## Migration Guide

### Applying the Migration

Run the Alembic migration to add the new fields:

```bash
# Using Alembic
alembic upgrade head

# Or using the migration script
python migrations/manage_migrations.py upgrade
```

### Migration Details

- **Migration File**: `migrations/versions/027_add_user_time_rounding_preferences.py`
- **Adds**: Three new columns to the `users` table
- **Safe**: Non-destructive, adds columns with default values
- **Rollback**: Supported via downgrade function

### Verifying Migration

```python
from app.models import User
from app import db

# Check if fields exist
user = User.query.first()
assert hasattr(user, 'time_rounding_enabled')
assert hasattr(user, 'time_rounding_minutes')
assert hasattr(user, 'time_rounding_method')

# Check default values
assert user.time_rounding_enabled == True
assert user.time_rounding_minutes == 1
assert user.time_rounding_method == 'nearest'
```

## Configuration

### Available Rounding Intervals

The following intervals are supported:
- `1` - No rounding (exact time)
- `5` - 5 minutes
- `10` - 10 minutes
- `15` - 15 minutes
- `30` - 30 minutes (half hour)
- `60` - 60 minutes (1 hour)

### Available Rounding Methods

Three methods are supported:
- `'nearest'` - Round to nearest interval
- `'up'` - Always round up (ceiling)
- `'down'` - Always round down (floor)

### Global Fallback Setting

If per-user rounding is not configured, the system uses the global setting:

```python
# In app/config.py
ROUNDING_MINUTES = int(os.environ.get('ROUNDING_MINUTES', 1))
```

## Testing

### Running Tests

```bash
# Run all time rounding tests
pytest tests/test_time_rounding*.py -v

# Run specific test suites
pytest tests/test_time_rounding.py -v  # Unit tests
pytest tests/test_time_rounding_models.py -v  # Model integration tests
pytest tests/test_time_rounding_smoke.py -v  # Smoke tests
```

### Test Coverage

The feature includes:
- **Unit Tests**: Core rounding logic (50+ test cases)
- **Model Tests**: Database integration and TimeEntry model
- **Smoke Tests**: End-to-end workflows and edge cases

## Examples

### Example 1: Freelancer with 15-Minute Billing

```python
# User settings
user.time_rounding_enabled = True
user.time_rounding_minutes = 15
user.time_rounding_method = 'nearest'

# Time entry: 62 minutes
# Result: 60 minutes (rounded to nearest 15-min interval)
```

### Example 2: Contractor with Round-Up Policy

```python
# User settings
user.time_rounding_enabled = True
user.time_rounding_minutes = 15
user.time_rounding_method = 'up'

# Time entry: 61 minutes
# Result: 75 minutes (rounded up to next 15-min interval)
```

### Example 3: Exact Time Tracking

```python
# User settings
user.time_rounding_enabled = False

# Time entry: 62 minutes 37 seconds
# Result: 62 minutes 37 seconds (3757 seconds, exact)
```

### Example 4: Conservative Billing

```python
# User settings
user.time_rounding_enabled = True
user.time_rounding_minutes = 30
user.time_rounding_method = 'down'

# Time entry: 62 minutes
# Result: 60 minutes (rounded down to previous 30-min interval)
```

## Troubleshooting

### Rounding Not Applied

**Issue**: Time entries are not being rounded despite settings being enabled.

**Solutions**:
1. Verify rounding is enabled: Check `user.time_rounding_enabled == True`
2. Check rounding interval: Ensure `user.time_rounding_minutes > 1`
3. Verify migration was applied: Check if columns exist in database
4. Clear cache and restart application

### Unexpected Rounding Results

**Issue**: Durations are rounded differently than expected.

**Solutions**:
1. Verify rounding method setting (nearest/up/down)
2. Check the actual rounding interval (minutes value)
3. Test with example calculations using the utility functions
4. Review the rounding method documentation

### Migration Fails

**Issue**: Alembic migration fails to apply.

**Solutions**:
1. Check database permissions
2. Verify no conflicting migrations
3. Run `alembic current` to check migration state
4. Try manual column addition as fallback
5. Check logs for specific error messages

## Best Practices

1. **Choose Appropriate Intervals**: Match your rounding to billing agreements
2. **Document Your Choice**: Note why you chose specific rounding settings
3. **Test Before Production**: Verify rounding behavior with test entries
4. **Communicate with Clients**: Ensure clients understand your rounding policy
5. **Review Regularly**: Periodically review if rounding settings still make sense
6. **Keep Records**: Document any changes to rounding preferences

## Future Enhancements

Potential improvements for future versions:
- Project-specific rounding overrides
- Time-of-day based rounding rules
- Client-specific rounding preferences
- Rounding reports and analytics
- Bulk update of historical entries with new rounding

## Support

For issues or questions:
1. Check this documentation first
2. Review test files for usage examples
3. Check the codebase in `app/utils/time_rounding.py`
4. Open an issue on the project repository

## Changelog

### Version 1.0 (2025-10-24)
- Initial implementation of per-user time rounding preferences
- Support for 6 rounding intervals (1, 5, 10, 15, 30, 60 minutes)
- Support for 3 rounding methods (nearest, up, down)
- UI integration in user settings page
- Comprehensive test coverage
- Full backward compatibility with global rounding settings

