# Overtime Tracking Feature

## Quick Start

The Overtime Tracking feature allows users to track hours worked beyond their standard workday.

### For Users

1. **Set Your Standard Hours**
   - Go to Settings → Overtime Settings
   - Enter your standard working hours per day (e.g., 8.0)
   - Click Save

2. **View Your Overtime**
   - Navigate to Reports → User Report
   - Select your date range
   - View overtime breakdown in the report table

### For Developers

**Key Files:**
- `app/utils/overtime.py` - Core calculation functions
- `app/models/user.py` - User model with standard_hours_per_day field
- `app/routes/reports.py` - Report route with overtime display
- `app/routes/analytics.py` - Analytics API endpoint
- `migrations/versions/031_add_standard_hours_per_day.py` - Database migration

**API Endpoint:**
```
GET /api/analytics/overtime?days=30
```

**Key Functions:**
```python
from app.utils.overtime import (
    calculate_daily_overtime,
    calculate_period_overtime,
    get_daily_breakdown,
    get_overtime_statistics
)
```

### Testing

```bash
# Run all overtime tests
pytest tests/test_overtime.py tests/test_overtime_smoke.py -v

# With coverage
pytest tests/test_overtime*.py --cov=app.utils.overtime --cov-report=html
```

### Documentation

- **Full Documentation**: [OVERTIME_FEATURE_DOCUMENTATION.md](../../OVERTIME_FEATURE_DOCUMENTATION.md)
- **Implementation Summary**: [OVERTIME_IMPLEMENTATION_SUMMARY.md](../../OVERTIME_IMPLEMENTATION_SUMMARY.md)

## How It Works

1. User sets standard hours per day in settings (default: 8.0)
2. System tracks all time entries as usual
3. When viewing reports, system calculates:
   - For each day: regular hours (up to standard) + overtime hours (beyond standard)
4. Reports display:
   - Total hours worked
   - Regular hours (green)
   - Overtime hours (orange)
   - Days with overtime

## Examples

### Example 1: Full-time Employee (8 hours/day)
- Monday: 8 hours → 8 regular, 0 overtime
- Tuesday: 10 hours → 8 regular, 2 overtime
- Wednesday: 7 hours → 7 regular, 0 overtime

### Example 2: Part-time Employee (6 hours/day)
- Monday: 6 hours → 6 regular, 0 overtime
- Tuesday: 7 hours → 6 regular, 1 overtime
- Wednesday: 5 hours → 5 regular, 0 overtime

## Configuration

**User Setting:** `standard_hours_per_day`
- Type: Float
- Default: 8.0
- Range: 0.5 to 24.0
- Location: User Settings → Overtime Settings

## Database

**Table:** `users`
**Column:** `standard_hours_per_day`
- Type: `FLOAT`
- Default: `8.0`
- Nullable: `NO`

**Migration:** `031_add_standard_hours_per_day`

## Features

✅ User-configurable standard hours  
✅ Automatic overtime calculation  
✅ Display in user reports  
✅ Analytics API endpoint  
✅ Daily overtime breakdown  
✅ Weekly overtime summaries  
✅ Comprehensive statistics  
✅ Full test coverage  
✅ Complete documentation  

## Future Enhancements

- Weekly overtime thresholds
- Overtime approval workflows
- Overtime pay rate calculations
- Email notifications for excessive overtime
- Overtime budget limits
- Export overtime reports

## Support

For questions or issues:
1. Review the [full documentation](../../OVERTIME_FEATURE_DOCUMENTATION.md)
2. Check test cases for examples
3. Open a GitHub issue

---

**Version:** 1.0.0  
**Status:** ✅ Production Ready  
**Last Updated:** October 27, 2025

