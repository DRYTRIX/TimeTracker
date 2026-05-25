# Workday sessions and working time limits

## Workday clock-in / clock-out

Employees can start and end their **workday** without selecting a project or client:

1. Open the **Dashboard** or **Timer** page.
2. Use **Start Workday** when arriving; **End Workday** when leaving.
3. Use the existing **Start Timer** flow for client/project time during the day.

Workday hours and project hours are shown **separately** on the dashboard (“At work today” vs “On projects today”). They are never added together.

### History

Personal workday history: `/workday/history`.

## Working time limits (admin)

**Admin → Settings → Time entry requirements → Working time limits**

- Enable daily/weekly caps (defaults: 10h / 48h).
- Optional email when limits are exceeded.
- Soft enforcement: timers keep running; employees submit a justification.

Per-user overrides: **User settings → Working time limits**.

### Employee flow

When a limit is exceeded, the user receives an email and sees a banner on the dashboard. They submit a reason at **Working time violations** (`/working-time/violations`).

### Admin review

**Admin → Working time limit reviews** (`/admin/working-time`): acknowledge submitted justifications.

### Background job

Every 15 minutes the system checks limits, sends notifications, and auto-closes workday sessions open longer than 18 hours.
