# Overtime Tracking Feature

## Quick Start

The Overtime Tracking feature allows users to track hours worked beyond their standard workday, either **per day** or **per week** (configurable).

### For Users

1. **Set Your Overtime Mode and Standard Hours**
   - Go to Settings → Overtime Settings
   - Choose **Calculate overtime by**: **Daily hours** or **Weekly hours**
   - **Daily**: Enter standard working hours per day (e.g., 8.0)
   - **Weekly**: Enter standard hours per week (e.g., 20 for part-time, 40 for full-time)
   - Click Save

2. **View Your Overtime**
   - Navigate to Reports → User Report
   - Select your date range
   - View overtime breakdown in the report table
   - **Accumulated overtime (YTD):** Your year-to-date overtime is shown on the main Dashboard (in the Month's Hours card), in Analytics (overtime API with `period=ytd`), and on the Workforce / Time-off page next to Leave Balances.

3. **Take Overtime as Paid Leave (Issue #560)**
   - Go to Workforce (or Time-off / Leave).
   - Your **Accumulated overtime (YTD)** is displayed next to Leave Balances.
   - Click **Take as paid leave** to scroll to the time-off request form with the "Overtime" leave type selected.
   - Enter the number of hours to request (capped at your YTD overtime); submit the request as usual. Approved requests record the hours taken as leave (no automatic balance deduction in v1).

### For Developers

**Key Files:**
- `app/utils/overtime.py` - Core calculation functions (including `get_week_start_for_date` for weekly mode)
- `app/models/user.py` - User model: `standard_hours_per_day`, `overtime_calculation_mode`, `standard_hours_per_week`
- `app/routes/reports.py` - Report route with overtime display
- `app/routes/analytics.py` - Analytics API endpoint
- `migrations/versions/031_add_standard_hours_per_day.py` - Database migration (daily)
- `migrations/versions/134_add_overtime_weekly_mode.py` - Weekly mode (Issue #551)

**API Endpoints:**
- `GET /api/analytics/overtime?days=30` — Overtime for the last N days.
- `GET /api/analytics/overtime?period=ytd` — Year-to-date accumulated overtime.
- `GET /api/dashboard/stats` and dashboard stats APIs include `overtime_ytd_hours`.

**Key Functions:**
```python
from app.utils.overtime import (
    calculate_daily_overtime,
    calculate_period_overtime,
    get_daily_breakdown,
    get_week_start_for_date,
    get_weekly_overtime_summary,
    get_overtime_statistics,
    get_overtime_ytd,           # YTD accumulated overtime
    get_overtime_last_12_months # Optional: last 12 months
)
```

### Testing

```bash
# Run all overtime tests (including YTD and overtime-as-leave)
pytest tests/test_overtime.py tests/test_overtime_smoke.py tests/test_overtime_leave.py -v

# With coverage
pytest tests/test_overtime*.py --cov=app.utils.overtime --cov-report=html
```

### Documentation

- **Full Documentation**: [OVERTIME_FEATURE_DOCUMENTATION.md](../../OVERTIME_FEATURE_DOCUMENTATION.md)
- **Implementation Summary**: [OVERTIME_IMPLEMENTATION_SUMMARY.md](../../OVERTIME_IMPLEMENTATION_SUMMARY.md)

## How It Works

1. User chooses **Daily** or **Weekly** overtime in settings and sets the corresponding standard hours.
2. System tracks all time entries as usual.
3. When viewing reports:
   - **Daily mode**: For each day, hours up to standard hours per day are regular; the rest is overtime.
   - **Weekly mode**: For each full week (using the user’s week start), hours up to standard hours per week are regular; the rest is overtime.
4. Reports display total hours, regular hours, overtime hours, and (in daily mode) days with overtime.

## Examples

### Example 1: Daily mode – Full-time (8 hours/day)
- Monday: 8 hours → 8 regular, 0 overtime
- Tuesday: 10 hours → 8 regular, 2 overtime
- Wednesday: 7 hours → 7 regular, 0 overtime

### Example 2: Daily mode – Part-time (6 hours/day)
- Monday: 6 hours → 6 regular, 0 overtime
- Tuesday: 7 hours → 6 regular, 1 overtime
- Wednesday: 5 hours → 5 regular, 0 overtime

### Example 3: Weekly mode (20 hours/week, e.g. 4 days)
- Monday: 5 h, Tuesday: 5 h, Wednesday: 5 h, Thursday: 5 h → 20 total → 20 regular, 0 overtime
- Monday: 6 h, Tuesday: 5 h, Wednesday: 5 h, Thursday: 5 h → 21 total → 20 regular, 1 overtime

## Configuration

**User Settings (Overtime):**
- `overtime_calculation_mode`: `"daily"` | `"weekly"` (default: `"daily"`)
- `standard_hours_per_day`: Float, 0.5–24, default 8.0 (used in daily mode)
- `standard_hours_per_week`: Float, 1–168, optional (used in weekly mode; if unset, derived as standard_hours_per_day × 5)
- Location: User Settings → Overtime Settings

## Database

**Table:** `users`
- `standard_hours_per_day`: `FLOAT`, default 8.0, NOT NULL
- `overtime_calculation_mode`: `VARCHAR(10)`, default `'daily'`, NOT NULL
- `standard_hours_per_week`: `FLOAT`, nullable

**Migrations:** `031_add_standard_hours_per_day`, `134_add_overtime_weekly_mode`, `136_seed_overtime_leave_type` (seeds "Overtime" leave type for take-as-paid-leave)

## Features

✅ User-configurable standard hours  
✅ Automatic overtime calculation  
✅ Display in user reports  
✅ Analytics API endpoint (including `period=ytd`)  
✅ **Accumulated overtime (YTD)** on Dashboard, Analytics, and Workforce  
✅ **Take overtime as paid leave** — Overtime leave type and request flow (Issue #560)  
✅ Daily overtime breakdown  
✅ Weekly overtime summaries  
✅ Comprehensive statistics  
✅ Full test coverage  
✅ Complete documentation  

## Future Enhancements

- Weekly overtime thresholds (implemented as optional weekly mode; see Issue #551)
- Stored overtime balance and deduction when overtime leave is approved (v1 records only)
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

**Version:** 1.2.0  
**Status:** ✅ Production Ready  
**Last Updated:** March 11, 2026

