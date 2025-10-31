# Budget Alerts & Forecasting

This document describes the Budget Alerts & Forecasting feature in the TimeTracker application.

## Overview

The Budget Alerts & Forecasting feature provides comprehensive budget monitoring and predictive analytics for projects with defined budgets. It helps project managers and administrators:

- Monitor budget consumption in real-time
- Receive automatic alerts when budget thresholds are exceeded
- Forecast project completion dates based on burn rates
- Analyze resource allocation and cost trends
- Make data-driven decisions about project budgets

## Features

### 1. Budget Monitoring

The system continuously monitors budget consumption for all active projects with defined budgets. Budget consumption is calculated based on:

- **Billable Time Entries**: Hours worked multiplied by the project's hourly rate
- **Project Costs**: Direct expenses (materials, travel, equipment, etc.)

### 2. Budget Alerts

Budget alerts are automatically generated when specific thresholds are reached:

#### Alert Types

1. **Warning (80%)**: Triggered when budget consumption reaches the configured threshold (default 80%)
   - Alert Level: Warning
   - Purpose: Early warning to allow corrective action

2. **Budget Reached (100%)**: Triggered when budget is fully consumed
   - Alert Level: Critical
   - Purpose: Immediate notification that budget limit has been reached

3. **Over Budget**: Triggered when budget is exceeded
   - Alert Level: Critical
   - Purpose: Alert that project has gone over budget

#### Alert Management

- Alerts are automatically created every 6 hours via a background task
- Duplicate alerts are prevented within a 24-hour window
- Alerts can be acknowledged by users with access to the project
- Acknowledged alerts are hidden from the active alerts list
- Alert history is preserved for reporting and audit purposes

### 3. Burn Rate Calculation

The burn rate feature calculates how quickly a project is consuming its budget:

- **Daily Burn Rate**: Average cost per day
- **Weekly Burn Rate**: Average cost per week
- **Monthly Burn Rate**: Average cost per month

Burn rates are calculated based on a configurable time period (default: 30 days) and include both time-based costs and direct project expenses.

### 4. Completion Date Estimation

The system estimates when a project's budget will be exhausted based on:

- Current burn rate
- Remaining budget
- Historical spending patterns

#### Confidence Levels

Estimates include a confidence level based on data consistency:

- **High Confidence**: Consistent spending pattern with sufficient historical data
- **Medium Confidence**: Moderate variation in spending pattern
- **Low Confidence**: High variation or insufficient historical data

### 5. Resource Allocation Analysis

Provides detailed breakdown of:

- Hours worked per team member
- Cost per team member
- Percentage contribution to total costs
- Number of time entries per team member
- Average hours per entry

This helps identify:
- Most resource-intensive team members
- Resource utilization patterns
- Cost distribution across the team

### 6. Cost Trend Analysis

Analyzes spending patterns over time with three granularities:

- **Daily**: Day-by-day cost breakdown
- **Weekly**: Week-by-week cost breakdown (default)
- **Monthly**: Month-by-month cost breakdown

#### Trend Indicators

- **Increasing**: Costs are trending upward
- **Decreasing**: Costs are trending downward
- **Stable**: Costs are relatively consistent
- **Insufficient Data**: Not enough data for trend analysis

### 7. Budget Status Dashboard

Central dashboard showing:

- Summary cards with key metrics
- Active budget alerts
- Project budget status table
- Quick access to detailed project analysis

## User Interface

### Budget Dashboard (`/budget/dashboard`)

Main entry point for budget monitoring with:

- Alert summary cards (unacknowledged, critical, warnings)
- Active alerts list with acknowledge functionality
- Project budget status table with progress bars
- Quick filters and refresh capability

### Project Budget Detail (`/budget/project/<project_id>`)

Detailed view for a specific project including:

- Budget status cards (total, consumed, remaining, status)
- Burn rate analysis panel
- Completion date estimation
- Interactive cost trend chart
- Resource allocation table
- Project-specific alerts

## API Endpoints

### GET `/budget/dashboard`
Display the main budget dashboard page

**Access**: Users with access to at least one budgeted project

### GET `/api/budget/burn-rate/<project_id>`
Get burn rate metrics for a project

**Parameters**:
- `days` (optional): Number of days to analyze (default: 30)

**Response**:
```json
{
  "daily_burn_rate": 400.50,
  "weekly_burn_rate": 2803.50,
  "monthly_burn_rate": 12015.00,
  "period_total": 12000.00,
  "period_days": 30,
  "start_date": "2025-10-01",
  "end_date": "2025-10-31"
}
```

### GET `/api/budget/completion-estimate/<project_id>`
Get estimated completion date based on burn rate

**Parameters**:
- `days` (optional): Number of days to analyze for burn rate (default: 30)

**Response**:
```json
{
  "estimated_completion_date": "2025-12-15",
  "days_remaining": 45,
  "budget_amount": 10000.00,
  "consumed_amount": 7500.00,
  "remaining_budget": 2500.00,
  "daily_burn_rate": 55.56,
  "confidence": "high",
  "message": "Based on 30 days of activity"
}
```

### GET `/api/budget/resource-allocation/<project_id>`
Get resource allocation analysis

**Parameters**:
- `days` (optional): Number of days to analyze (default: 30)

**Response**:
```json
{
  "users": [
    {
      "user_id": 1,
      "username": "John Doe",
      "hours": 120.50,
      "cost": 12050.00,
      "cost_percentage": 60.5,
      "hours_percentage": 55.2,
      "entry_count": 45,
      "average_hours_per_entry": 2.68
    }
  ],
  "total_hours": 218.00,
  "total_cost": 19900.00,
  "period_days": 30,
  "hourly_rate": 100.00
}
```

### GET `/api/budget/cost-trends/<project_id>`
Get cost trend analysis

**Parameters**:
- `days` (optional): Number of days to analyze (default: 90)
- `granularity` (optional): 'day', 'week', or 'month' (default: 'week')

**Response**:
```json
{
  "periods": [
    {"period": "2025-W40", "cost": 1250.00},
    {"period": "2025-W41", "cost": 1380.00}
  ],
  "trend_direction": "increasing",
  "average_cost_per_period": 1315.00,
  "trend_percentage": 10.4,
  "granularity": "week",
  "period_count": 12
}
```

### GET `/api/budget/status/<project_id>`
Get comprehensive budget status

**Response**:
```json
{
  "budget_amount": 10000.00,
  "consumed_amount": 8250.00,
  "remaining_amount": 1750.00,
  "consumed_percentage": 82.5,
  "status": "critical",
  "threshold_percent": 80,
  "project_name": "Project Alpha",
  "project_id": 123
}
```

### GET `/api/budget/alerts`
Get budget alerts

**Parameters**:
- `project_id` (optional): Filter by project ID
- `acknowledged` (optional): Filter by acknowledgment status (default: false)

**Response**:
```json
{
  "alerts": [
    {
      "id": 1,
      "project_id": 123,
      "project_name": "Project Alpha",
      "alert_type": "warning_80",
      "alert_level": "warning",
      "budget_consumed_percent": 82.5,
      "budget_amount": 10000.00,
      "consumed_amount": 8250.00,
      "message": "Warning: Project has consumed 82.5% of budget",
      "is_acknowledged": false,
      "created_at": "2025-10-31T10:30:00"
    }
  ],
  "count": 1
}
```

### POST `/api/budget/alerts/<alert_id>/acknowledge`
Acknowledge a budget alert

**Response**:
```json
{
  "message": "Alert acknowledged successfully",
  "alert": { /* alert object */ }
}
```

### POST `/api/budget/check-alerts/<project_id>`
Manually check and create alerts for a project (admin only)

**Response**:
```json
{
  "message": "Checked alerts for project Project Alpha",
  "alerts_created": 1,
  "alerts": [ /* created alerts */ ]
}
```

### GET `/api/budget/summary`
Get summary of all budget alerts and project statuses

**Response**:
```json
{
  "total_projects": 15,
  "healthy": 8,
  "warning": 4,
  "critical": 2,
  "over_budget": 1,
  "total_budget": 150000.00,
  "total_consumed": 98500.00,
  "projects": [ /* budget status for each project */ ],
  "alert_stats": {
    "total_alerts": 12,
    "unacknowledged_alerts": 5,
    "critical_alerts": 3
  }
}
```

## Database Schema

### budget_alerts Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| project_id | Integer | Foreign key to projects table |
| alert_type | String(20) | Type of alert (warning_80, warning_100, over_budget) |
| alert_level | String(20) | Severity level (info, warning, critical) |
| budget_consumed_percent | Numeric(5,2) | Percentage of budget consumed |
| budget_amount | Numeric(10,2) | Total budget at time of alert |
| consumed_amount | Numeric(10,2) | Amount consumed at time of alert |
| message | Text | Alert message |
| is_acknowledged | Boolean | Whether alert has been acknowledged |
| acknowledged_by | Integer | User ID who acknowledged (nullable) |
| acknowledged_at | DateTime | When alert was acknowledged (nullable) |
| created_at | DateTime | When alert was created |

**Indexes**:
- `ix_budget_alerts_project_id` on project_id
- `ix_budget_alerts_acknowledged_by` on acknowledged_by
- `ix_budget_alerts_created_at` on created_at
- `ix_budget_alerts_is_acknowledged` on is_acknowledged
- `ix_budget_alerts_alert_type` on alert_type

## Background Tasks

### Budget Alert Checking

The system runs a scheduled task every 6 hours to check all active projects with budgets:

```python
# Scheduled at: 00:00, 06:00, 12:00, 18:00 daily
check_project_budget_alerts()
```

This task:
1. Queries all active projects with budgets
2. Calculates current budget consumption
3. Checks against thresholds
4. Creates alerts if thresholds are exceeded
5. Prevents duplicate alerts within 24 hours

## Configuration

### Project Budget Settings

Budget alerts can be configured per project:

- **Budget Amount**: Total budget allocated to the project
- **Budget Threshold**: Percentage at which to trigger warning alerts (default: 80%)

These settings can be configured when creating or editing a project.

### System Configuration

The background task schedule can be modified in `app/utils/scheduled_tasks.py`:

```python
scheduler.add_job(
    func=check_project_budget_alerts,
    trigger='cron',
    hour='*/6',  # Modify this to change frequency
    minute=0,
    id='check_budget_alerts',
    name='Check project budget alerts',
    replace_existing=True
)
```

## Permissions

### Access Control

- **Admin Users**: Full access to all budget features for all projects
- **Regular Users**: Access to budget information for projects they have worked on
- **Budget Dashboard**: Available to all authenticated users
- **Alert Acknowledgment**: Available to users with access to the project
- **Manual Alert Checking**: Admin only

## Usage Examples

### Viewing Budget Dashboard

1. Navigate to `/budget/dashboard`
2. View summary cards showing total alerts and project counts
3. Review active alerts list
4. Click on project names to see detailed analysis

### Monitoring a Specific Project

1. From the budget dashboard, click "Details" for a project
2. Review the budget status cards
3. Analyze the burn rate to understand spending patterns
4. Check the completion estimate to plan accordingly
5. Review resource allocation to identify high-cost team members
6. Examine cost trends to spot patterns

### Acknowledging Alerts

1. View an active alert on the dashboard or project detail page
2. Click the "Acknowledge" button
3. The alert is marked as acknowledged and removed from active alerts list

### Manual Alert Check (Admin)

1. Navigate to a project's budget detail page
2. Use the API endpoint `/api/budget/check-alerts/<project_id>`
3. System checks current budget status and creates alerts if needed

## Best Practices

1. **Set Realistic Budgets**: Ensure project budgets are realistic and based on historical data
2. **Configure Appropriate Thresholds**: Adjust warning thresholds based on project risk tolerance
3. **Regular Monitoring**: Review the budget dashboard regularly to catch issues early
4. **Acknowledge Alerts**: Acknowledge alerts after reviewing them to keep the dashboard clean
5. **Analyze Trends**: Use cost trend analysis to identify patterns and adjust resource allocation
6. **Review Resource Allocation**: Regularly review which team members are consuming the most budget
7. **Act on Warnings**: Take corrective action when warning alerts are triggered

## Troubleshooting

### No Alerts Being Generated

- Verify that projects have `budget_amount` set
- Check that background scheduler is running
- Verify that budget consumption actually exceeds thresholds
- Check logs for any errors in the scheduled task

### Inaccurate Burn Rate Calculations

- Ensure time entries have `billable` flag set correctly
- Verify that project `hourly_rate` is set
- Check that time entries have `end_time` set (completed entries)
- Review the analysis period (try different `days` values)

### Missing Projects in Dashboard

- Verify project has `budget_amount` set
- Check that project `status` is 'active'
- For non-admin users, ensure they have time entries on the project

### Completion Estimate Shows "Low Confidence"

- This indicates inconsistent spending patterns
- Increase the analysis period (`days` parameter)
- Ensure sufficient time entries exist
- Review actual spending patterns for irregularities

## Migration

The budget alerts feature requires a database migration:

```bash
# Run the migration
alembic upgrade head

# Or use the manage migrations script
python migrations/manage_migrations.py upgrade
```

This creates the `budget_alerts` table with all necessary indexes.

## Testing

The feature includes comprehensive tests:

- **Unit Tests**: `tests/test_budget_forecasting.py` - Tests all utility functions
- **Model Tests**: `tests/test_budget_alert_model.py` - Tests BudgetAlert model
- **Smoke Tests**: `tests/test_budget_alerts_smoke.py` - Integration and end-to-end tests

Run tests with:

```bash
pytest tests/test_budget_forecasting.py
pytest tests/test_budget_alert_model.py
pytest tests/test_budget_alerts_smoke.py
```

## Future Enhancements

Potential future improvements:

1. **Email Notifications**: Send email alerts when budget thresholds are exceeded
2. **Custom Alert Thresholds**: Allow multiple custom thresholds per project
3. **Budget Forecasting AI**: Use machine learning to improve completion date predictions
4. **Budget Templates**: Create reusable budget templates for similar projects
5. **Multi-Currency Support**: Handle projects with different currencies
6. **Budget Revisions**: Track budget changes and revisions over time
7. **What-If Analysis**: Simulate different scenarios and their impact on budget
8. **Export Reports**: Generate PDF/Excel reports of budget analysis
9. **Budget Rollover**: Automatically rollover unused budget to related projects
10. **Team Budget Limits**: Set budget limits per team member

## Related Documentation

- [Project Management](./PROJECT_MANAGEMENT.md)
- [Time Tracking](./TIME_TRACKING.md)
- [Reports](./REPORTS.md)
- [API Documentation](./API.md)

