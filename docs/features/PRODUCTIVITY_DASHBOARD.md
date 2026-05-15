# Personal productivity dashboard

## Overview

The **My productivity** page (`/dashboard/productivity`) is a dedicated view for the signed-in user’s own time-tracking patterns. It is separate from the main dashboard timer and summary widgets.

Navigation: sidebar → **My productivity** (chart-line icon).

## What it shows

### Summary cards

- **Today’s hours** — completed time for the user’s local calendar day, with a progress arc against `standard_hours_per_day` (user preference, default 8h). Shows a “Timer running” indicator when an active timer exists.
- **This week** — hours logged Monday through today vs weekly goal (`WeeklyTimeGoal` for the current week when set, otherwise `standard_hours_per_day × 5`, default 40h). Progress bar reflects billable share.
- **Streak** — consecutive local days with at least one completed entry (today counts only if hours &gt; 0; otherwise the streak starts from yesterday). Shows best-ever streak.
- **Average session** — mean duration of completed entries in the last 30 days (entries under 5 minutes excluded).

### Charts and panels

- **Daily hours** — Chart.js bar chart for the last 14 days with a dashed goal reference line.
- **Project breakdown** — doughnut chart of top 8 projects (last 30 days) with HTML legend.
- **Focus** — most productive hour (with 24-bar sparkline), day of week, longest session, entries per active day, tracked days this month.
- **Activity heatmap** — GitHub-style grid for the last 12 weeks (levels 0–4 by hours per day).
- **Insights** — up to four plain-text tips derived from the same data (week-over-week change, streak, peak hour, top project share, billable rate).

## Data and timezone

All bucketing uses the user’s timezone (`User.timezone`, falling back to application timezone). Completed entries only (`end_time` is set).

Implementation: [`app/services/productivity_service.py`](../../app/services/productivity_service.py).

## API

```
GET /api/productivity/stats
```

**Authentication:** session cookie (`@login_required`).

**Query parameters:**

| Param | Default | Max | Purpose |
|-------|---------|-----|---------|
| `period` | 30 | 90 | Days for focus stats and project breakdown |

**Response (200):**

```json
{
  "ok": true,
  "period": 30,
  "summary": { "today_hours": 0, "week_hours": 0, "week_goal_hours": 40, "week_goal_percent": 0, "active_timer": null, "billable_percent_week": 0, "top_project_week": null },
  "daily_breakdown": [{ "date": "2026-05-01", "hours": 0, "billable_hours": 0, "entry_count": 0, "goal_hours": 8 }],
  "streak": { "current_streak": 0, "longest_streak": 0, "tracked_days_this_month": 0, "total_days_this_month": 15 },
  "focus": { "avg_session_length_minutes": 0, "longest_session_hours": 0, "entries_per_day": 0, "most_productive_hour": null, "most_productive_day": null, "hour_distribution": [] },
  "projects": [],
  "heatmap": [{ "date": "2026-02-15", "hours": 0, "level": 0 }],
  "insights": []
}
```

**Caching:** when `app.utils.cache.get_cache()` is available, responses are cached for **5 minutes** per `user_id` and `period`, except when `summary.active_timer` is set (so live timer state stays fresh).

**Errors:** `{ "ok": false, "error": "..." }` with HTTP 500 on unexpected failure. The service layer never raises; empty users get zeros and empty lists.

## Client behaviour

The page embeds initial JSON from the server render, then:

- **Refresh** button calls `GET /api/productivity/stats` and updates Chart.js datasets in place.
- Auto-refresh every **5 minutes** when the tab is visible (`document.visibilityState`).
- Auto-refresh every **60 seconds** when an active timer is running.

Template: [`app/templates/main/productivity_dashboard.html`](../../app/templates/main/productivity_dashboard.html).

## Related features

- Main dashboard **Value insights** widget uses [`StatsService`](../../app/services/stats_service.py) and `GET /api/stats/value-dashboard` (different aggregates).
- Per-project forecasting on the project detail page: [Budget alerts & forecasting](../BUDGET_ALERTS_AND_FORECASTING.md) and `GET /api/projects/<id>/forecast`.
