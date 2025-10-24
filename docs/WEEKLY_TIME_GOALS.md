# Weekly Time Goals

## Overview

The Weekly Time Goals feature allows users to set and track weekly hour targets, helping them manage workload and maintain work-life balance. Users can create goals for different weeks, monitor progress in real-time, and review their historical performance.

## Features

### Goal Management

- **Create Weekly Goals**: Set target hours for any week
- **Track Progress**: Real-time progress tracking against targets
- **Status Management**: Automatic status updates (active, completed, failed, cancelled)
- **Notes**: Add context and notes to goals
- **Historical View**: Review past goals and performance

### Dashboard Integration

- **Weekly Goal Widget**: Display current week's progress on the dashboard
- **Quick Actions**: Create or view goals directly from the dashboard
- **Visual Progress**: Color-coded progress bars and statistics

### Analytics

- **Success Rate**: Track completion rate over time
- **Daily Breakdown**: See hours logged per day
- **Average Performance**: View average target vs actual hours
- **Streak Tracking**: Monitor consecutive weeks of completed goals

## User Guide

### Creating a Weekly Goal

1. Navigate to **Weekly Goals** from the sidebar
2. Click **New Goal** button
3. Enter your target hours (e.g., 40 for full-time)
4. Optionally select a specific week (defaults to current week)
5. Add notes if desired (e.g., "Vacation week, reduced hours")
6. Click **Create Goal**

### Quick Presets

The create page includes quick preset buttons for common targets:
- 20 hours (half-time)
- 30 hours (part-time)
- 40 hours (full-time)
- 50 hours (overtime)

### Viewing Goal Progress

#### Dashboard Widget

The dashboard shows your current week's goal with:
- Progress bar
- Actual vs target hours
- Remaining hours
- Days remaining
- Average hours per day needed to reach goal

#### Detailed View

Click on any goal to see:
- Complete week statistics
- Daily breakdown of hours
- All time entries for that week
- Progress visualization

### Editing Goals

1. Navigate to the goal (from Weekly Goals page or dashboard)
2. Click **Edit**
3. Modify target hours, status, or notes
4. Click **Save Changes**

**Note**: Week dates cannot be changed after creation. Create a new goal for a different week instead.

### Understanding Goal Status

Goals automatically update their status based on progress and time:

- **Active**: Current or future week, not yet completed
- **Completed**: Goal met (actual hours ≥ target hours)
- **Failed**: Week ended without meeting goal
- **Cancelled**: Manually cancelled by user

## API Endpoints

### Get Current Week Goal

```http
GET /api/goals/current
```

Returns the goal for the current week for the authenticated user.

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "target_hours": 40.0,
  "actual_hours": 25.5,
  "week_start_date": "2025-10-20",
  "week_end_date": "2025-10-26",
  "week_label": "Oct 20 - Oct 26, 2025",
  "status": "active",
  "progress_percentage": 63.8,
  "remaining_hours": 14.5,
  "days_remaining": 3,
  "average_hours_per_day": 4.83
}
```

### List Goals

```http
GET /api/goals?limit=12&status=active
```

List goals for the authenticated user.

**Query Parameters:**
- `limit` (optional): Number of goals to return (default: 12)
- `status` (optional): Filter by status (active, completed, failed, cancelled)

**Response:**
```json
[
  {
    "id": 1,
    "target_hours": 40.0,
    "actual_hours": 25.5,
    "status": "active",
    ...
  },
  ...
]
```

### Get Goal Statistics

```http
GET /api/goals/stats
```

Get aggregated statistics about user's goals.

**Response:**
```json
{
  "total_goals": 12,
  "completed": 8,
  "failed": 3,
  "active": 1,
  "cancelled": 0,
  "completion_rate": 72.7,
  "average_target_hours": 40.0,
  "average_actual_hours": 38.5,
  "current_streak": 3
}
```

### Get Specific Goal

```http
GET /api/goals/{goal_id}
```

Get details for a specific goal.

## Database Schema

### weekly_time_goals Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| user_id | Integer | Foreign key to users table |
| target_hours | Float | Target hours for the week |
| week_start_date | Date | Monday of the week |
| week_end_date | Date | Sunday of the week |
| status | String(20) | Goal status (active, completed, failed, cancelled) |
| notes | Text | Optional notes about the goal |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

**Indexes:**
- `ix_weekly_time_goals_user_id` on `user_id`
- `ix_weekly_time_goals_week_start_date` on `week_start_date`
- `ix_weekly_time_goals_status` on `status`
- `ix_weekly_time_goals_user_week` on `(user_id, week_start_date)` (composite)

## Best Practices

### Setting Realistic Goals

1. **Consider Your Schedule**: Account for meetings, holidays, and other commitments
2. **Start Conservative**: Begin with achievable targets and adjust based on experience
3. **Account for Non-Billable Time**: Include time for admin tasks, learning, etc.
4. **Review and Adjust**: Use historical data to set more accurate future goals

### Using Goals Effectively

1. **Check Progress Daily**: Review your dashboard widget each morning
2. **Adjust Behavior**: If behind, plan focused work sessions
3. **Celebrate Wins**: Acknowledge completed goals
4. **Learn from Misses**: Review failed goals to understand what went wrong

### Goal Recommendations

- **Full-Time (40h/week)**: Standard work week (8h/day × 5 days)
- **Part-Time (20-30h/week)**: Adjust based on your arrangement
- **Flexible**: Vary by week based on project demands and personal schedule
- **Overtime (45-50h/week)**: Use sparingly; monitor for burnout

## Technical Implementation

### Model: WeeklyTimeGoal

**Location**: `app/models/weekly_time_goal.py`

**Key Properties:**
- `actual_hours`: Calculated from time entries
- `progress_percentage`: (actual_hours / target_hours) × 100
- `remaining_hours`: target_hours - actual_hours
- `is_completed`: actual_hours ≥ target_hours
- `days_remaining`: Days left in the week
- `average_hours_per_day`: Avg hours per day needed to meet goal

**Key Methods:**
- `update_status()`: Auto-update status based on progress and date
- `get_current_week_goal(user_id)`: Get current week's goal for user
- `get_or_create_current_week(user_id, default_target_hours)`: Get or create current week goal

### Routes: weekly_goals Blueprint

**Location**: `app/routes/weekly_goals.py`

**Web Routes:**
- `GET /goals` - Goals overview page
- `GET /goals/create` - Create goal form
- `POST /goals/create` - Create goal handler
- `GET /goals/<id>` - View specific goal
- `GET /goals/<id>/edit` - Edit goal form
- `POST /goals/<id>/edit` - Update goal handler
- `POST /goals/<id>/delete` - Delete goal handler

**API Routes:**
- `GET /api/goals/current` - Get current week goal
- `GET /api/goals` - List goals
- `GET /api/goals/<id>` - Get specific goal
- `GET /api/goals/stats` - Get goal statistics

### Templates

**Location**: `app/templates/weekly_goals/`

- `index.html` - Goals overview and history
- `create.html` - Create new goal
- `edit.html` - Edit existing goal
- `view.html` - Detailed goal view with daily breakdown

### Dashboard Widget

**Location**: `app/templates/main/dashboard.html`

Displays current week's goal with:
- Progress bar
- Key statistics
- Quick access links

## Migration

The feature is added via Alembic migration `027_add_weekly_time_goals.py`.

To apply the migration:

```bash
# Using make
make db-upgrade

# Or directly with alembic
alembic upgrade head
```

## Testing

### Running Tests

```bash
# All weekly goals tests
pytest tests/test_weekly_goals.py -v

# Specific test categories
pytest tests/test_weekly_goals.py -m unit
pytest tests/test_weekly_goals.py -m models
pytest tests/test_weekly_goals.py -m smoke
```

### Test Coverage

The test suite includes:
- **Model Tests**: Goal creation, calculations, status updates
- **Route Tests**: CRUD operations via web interface
- **API Tests**: All API endpoints
- **Integration Tests**: Dashboard widget, relationships

## Troubleshooting

### Goal Not Showing on Dashboard

**Issue**: Current week goal created but not visible on dashboard.

**Solutions**:
1. Refresh the page to reload goal data
2. Verify the goal is for the current week (check week_start_date)
3. Ensure goal status is not 'cancelled'

### Progress Not Updating

**Issue**: Logged time but progress bar hasn't moved.

**Solutions**:
1. Ensure time entries have end_time set (not active timers)
2. Verify time entries are within the week's date range
3. Check that time entries belong to the correct user
4. Refresh the page to recalculate

### Cannot Create Goal for Week

**Issue**: Error when creating goal for specific week.

**Solutions**:
1. Check if a goal already exists for that week
2. Verify target_hours is positive
3. Ensure week_start_date is a Monday (if specified)

## Future Enhancements

Potential future improvements:
- Goal templates (e.g., "Standard Week", "Light Week")
- Team goals and comparisons
- Goal recommendations based on historical data
- Notifications when falling behind
- Integration with calendar for automatic adjustments
- Monthly and quarterly goal aggregations
- Export goal reports

## Related Features

- **Time Tracking**: Time entries count toward weekly goals
- **Dashboard**: Primary interface for goal monitoring
- **Reports**: View time data that feeds into goals
- **User Preferences**: Week start day affects goal calculations

## Support

For issues or questions:
1. Check the [FAQ](../README.md#faq)
2. Review [Time Tracking documentation](TIME_TRACKING.md)
3. Open an issue on GitHub
4. Contact the development team

---

**Last Updated**: October 24, 2025
**Feature Version**: 1.0
**Migration**: 027_add_weekly_time_goals

