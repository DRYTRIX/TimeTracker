# Smart in-app notifications

Session-based reminders to improve daily tracking habits. Separate from **email** “Remind me to log time at end of day” (that flow is unchanged).

## Enabling for users

1. Open **Settings → Notifications**.
2. Under **In-app reminders (toasts)**, turn on **Enable smart notifications on this device**.
3. Choose which kinds to show:
   - No-tracking nudge (configurable hour window)
   - Long-running timer alert
   - Daily summary (hours logged today)
   - **Break reminder** — while a timer is running, nudge every N minutes (15–240, default 60)
   - **End-of-day wrap-up** — reminder near your configured end-of-day time with hours logged today
   - **Missed workday clock-in** — on expected work days (Mon–Fri, excluding holidays and approved time off), nudge if **Start Workday** was not pressed by your configured time (default 09:30)
4. Optionally enable **browser notifications** (requires permission in the browser). When push subscriptions exist and VAPID keys are configured, a background job can deliver the same actionable reminders via Web Push (see below).

Optional **email** for missed clock-in: **Email me if I forgot to start my workday** (separate from the in-app toggle; uses the same reminder time).

Optional **HH:MM** overrides apply to the **hour** used for time-window checks (same idea as the email reminder: the app uses the first `SMART_NOTIFY_SCHEDULER_SLOT_MINUTES` of that local hour). If left blank, server defaults from configuration apply.

## HTTP API (session auth)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/notifications` | Returns `{ "notifications": [...], "meta": { ... } }` when the feature is enabled for the user; empty list when disabled. |
| `POST` | `/api/notifications/dismiss` | JSON body: `{ "kind": "<kind>", "local_date": "YYYY-MM-DD" }`. Omit `local_date` to use the server-derived “today” in the user’s timezone. |

Stable `kind` values:

| Kind | When it fires |
|------|----------------|
| `no_tracking_today` | In the no-tracking hour window, no completed entries today, no active timer |
| `timer_running_long` | Active timer exceeds `SMART_NOTIFY_LONG_TIMER_HOURS` |
| `daily_summary` | In the summary hour window |
| `break_reminder` | Break reminder enabled, active timer running ≥ interval; once per interval bucket per timer |
| `end_of_day_reminder` | End-of-day reminder enabled, within the end-of-day hour window |
| `missed_clock_in` | Missed workday reminder enabled, expected work day, no work period started yet, within reminder time window |

`GET /api/summary/today` uses the same **user-local calendar day** as the notification service (for totals of **completed** entries).

## Server configuration (environment)

All optional; defaults are defined on `Config` in [`app/config.py`](../../app/config.py).

| Variable | Role |
|----------|------|
| `SMART_NOTIFY_MAX_PER_DAY` | Max notifications returned per request (default 2). |
| `SMART_NOTIFY_NO_TRACKING_AFTER` | Default `HH:MM` hour for the no-tracking nudge (default `16:00`). |
| `SMART_NOTIFY_SUMMARY_AT` | Default `HH:MM` hour for the daily summary window (default `18:00`). |
| `SMART_NOTIFY_END_OF_DAY_AT` | Default `HH:MM` hour for the end-of-day wrap-up window (default `17:00`). |
| `SMART_NOTIFY_MISSED_CLOCK_IN_AT` | Default `HH:MM` for the missed workday clock-in window (default `09:30`). |
| `SMART_NOTIFY_LONG_TIMER_HOURS` | Hours after which an active timer triggers the long-timer alert (default `4`). |
| `SMART_NOTIFY_SCHEDULER_SLOT_MINUTES` | Length of the firing window at the start of the configured hour (default `30`). |

Per-user overrides in **Settings**: `smart_notify_no_tracking_after`, `smart_notify_summary_at`, `smart_notify_end_of_day_time`, `smart_notify_break_interval_minutes`, `smart_notify_missed_clock_in_at`. Toggles: `smart_notify_missed_clock_in` (in-app), `notification_missed_clock_in` (email).

## Database

- Migration **`150_add_smart_notifications`**: smart notification columns on `users`, table `user_smart_notification_dismissals`.
- Migration **`154_add_smart_notify_break_and_eod`**: `smart_notify_break_reminder`, `smart_notify_break_interval_minutes`, `smart_notify_end_of_day`, `smart_notify_end_of_day_time` on `users`; widens `user_smart_notification_dismissals.local_date` to 64 characters so break reminders can store interval bucket keys (`break_<timer_id>_<bucket>`).
- Migration **`165_add_missed_clock_in_notifications`**: `smart_notify_missed_clock_in`, `smart_notify_missed_clock_in_at`, `notification_missed_clock_in` on `users`.

## Frontend

Two complementary clients:

1. **[`app/static/smart-notifications.js`](../../app/static/smart-notifications.js)** — Polls `/api/notifications` on an interval (default 10 minutes) and shows server-driven toasts via `toastManager`. Dismissals are sent when the toast closes (including auto-dismiss). Optional browser notifications when enabled and permission granted.

2. **[`app/static/idle.js`](../../app/static/idle.js)** — Idle detection (stop timer when inactive) plus additional reminder toasts:
   - **No timer** (`no_tracking_today`) — blue toast every 5 minutes when eligible; “Start timer” / dismiss (dismiss calls API with today’s date).
   - **Break** (`break_reminder`) — purple toast checked each minute while a timer runs; “Pause timer”, “Snooze 15 min” (client-side), dismiss.
   - **End of day** (`end_of_day_reminder`) — green toast every 5 minutes when eligible; “View entries” / dismiss.

   Only one reminder toast is shown at a time. `/api/notifications` is fetched at most once per 5-minute window (shared cache). Flags reset at local midnight.

[`app/static/toast-notifications.js`](../../app/static/toast-notifications.js) implements the optional `onDismiss` hook on `toastManager.show`.

## Background push (optional)

When the push notifications blueprint is loaded and users have `smart_notifications_enabled` plus at least one of break, end-of-day, no-tracking, or missed-clock-in reminders, APScheduler runs **`send_smart_reminder_push_notifications`** every 15 minutes ([`app/utils/scheduled_tasks.py`](../../app/utils/scheduled_tasks.py), job id `smart_reminder_push`). It calls `NotificationService.build_for_user` and sends `info` / `warning` payloads to registered push subscriptions via **pywebpush** when `VAPID_PUBLIC_KEY` and `VAPID_PRIVATE_KEY` are set. Missing push module, pywebpush, or VAPID configuration is skipped without error.

Hourly job **`process_missed_clock_in`** sends email when `notification_missed_clock_in` is enabled and the user has not started their workday on an expected work day.
