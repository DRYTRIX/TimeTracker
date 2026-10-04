# Timezone Convention

Short design note for datetime handling in TimeTracker. Goal: avoid silent “wrong day” bugs near midnight and DST without a full codebase migration.

## Current state

| Area | Practice |
|------|----------|
| **Time entries** | Stored as **naive datetimes in app-local time**. `TimeEntry` uses a naive `local_now()` (app TZ with `tzinfo` stripped) for `start_time`, `end_time`, timestamps, etc. |
| **App timezone** | From `Settings.timezone`, else env `TZ` (default `Europe/Rome`). See `get_app_timezone()`. |
| **Widespread legacy** | Many call sites still use `datetime.utcnow()` (naive UTC). Do **not** mass-replace these in one change. |
| **Helpers** | Prefer `app/utils/timezone.py` over ad-hoc `utcnow` / `date.today()` for new or touched code. |

Naive local storage means calendar queries (“today”, “this week”) must use the **same** timezone as the data. Mixing `utcnow().date()` with app-local entry times shifts day boundaries for non-UTC deployments.

## Target convention (pick one per change; prefer the first for new code)

1. **Preferred for new code:** timezone-aware **UTC** (`datetime.now(timezone.utc)`), convert at the boundary for display or comparison with app-local data via helpers below.
2. **Acceptable while data remains naive local:** stay consistent with **app-local naive** — use `local_now()` / `now_in_app_timezone()` (and strip tz only when writing columns that expect naive local).

Do not invent a third scheme (e.g. “server local” via bare `date.today()` or `datetime.now()` without a zone).

When touching a module, align that module’s *new* paths with one convention and document assumptions in comments if comparing across storage styles.

## Existing helpers (`app/utils/timezone.py`)

| Helper | Use |
|--------|-----|
| `get_app_timezone()` / `get_timezone_obj()` | Resolve configured app TZ name / `ZoneInfo`. |
| `now_in_app_timezone()` | Aware “now” in app TZ. |
| `local_now()` | Alias of `now_in_app_timezone()` in this module (**aware**). Note: `app.models.time_entry.local_now` is a separate **naive** helper for DB defaults. |
| `now_in_user_timezone(user)` / `get_timezone_for_user(user)` | Per-user TZ when preferences matter (reminders, UI). |
| `utc_to_local` / `local_to_utc` | Convert between UTC and app TZ. |
| `utc_to_user_local` / `user_local_to_utc` / `convert_app_datetime_to_user` | User-facing conversions. |
| `parse_local_datetime*` / `parse_user_local_datetime*` | Form input → storage. |
| `format_local_datetime` / `format_user_datetime` | Display. |

Import from `app.utils.timezone` unless you specifically need the naive DB helper on `TimeEntry`.

## Scheduled jobs and “today”

Jobs that decide overdue invoices, recurring invoice runs, weekly summary windows, task deadlines, holiday sync ranges, quote expiry, etc. must use **app timezone** for calendar dates:

```python
from app.utils.timezone import now_in_app_timezone  # or local_now

today = now_in_app_timezone().date()
```

**Do not** use `datetime.utcnow().date()` or bare `date.today()` for those boundaries — they follow UTC or the host OS zone, not `Settings.timezone` / `TZ`.

User-scoped reminders (e.g. “log time today” in the user’s zone) should keep using `now_in_user_timezone(user)` and that user’s local day.

Absolute timestamps (e.g. “is this schedule due yet?” against a stored `next_run_at`) are separate from calendar “today”; change those only when you know how the stored value is zoned.

## Scope discipline

- Fix “today” / date-boundary call sites in scheduled jobs and similar calendar logic when you touch them.
- Prefer helpers in new features and refactors.
- Do **not** rewrite hundreds of `utcnow` call sites in one PR; migrate incrementally with clear storage semantics.
