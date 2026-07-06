# Workday sessions and working time limits

## Workday clock-in / clock-out

Employees can start and end their **workday** without selecting a project or client:

1. Open the **Dashboard** or **Timer** page.
2. Use **Start Workday** when arriving; **End Workday** when leaving.
3. Use the existing **Start Timer** flow for client/project time during the day.

Workday hours and project hours are shown **separately** on the dashboard (“At work today” vs “On projects today”). They are never added together.

### History and corrections

Personal attendance history: `/workday/history`.

- **Forgot to clock in today:** press **Start Workday**, then request a correction to adjust the start time on an existing work period.
- **Missing day entirely:** use **Request missing workday** on the history page (date, start/end times, reason). An admin approves under **Attendance corrections** (`/admin/attendance/corrections`).

Enable **missed workday reminders** under **Settings → Notifications** (in-app smart notification and/or email).

### Slack attendance (optional)

Admins can enable workspace-level Slack slash commands (`/in`, `/brb`,
`/back`, `/out`) so employees clock in/out from a dedicated channel.
Successful commands post in-channel confirmations; records use
`source=slack`. See [SLACK_ATTENDANCE.md](../integrations/SLACK_ATTENDANCE.md).

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
