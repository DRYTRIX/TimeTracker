# Slack Attendance Integration

Workspace-level Slack slash commands for employee attendance tracking.

## Commands

| Command | Action |
|---------|--------|
| `/in` | Clock in (start workday) |
| `/brb` | Start a break |
| `/back` | End break (return to work) |
| `/out` | Clock out (end workday) |

Successful commands post an **in-channel** confirmation so the attendance channel acts as a shared log. Errors are shown only to the user who ran the command (ephemeral).

## Slack App Setup

### 1. Create a Slack app

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app for your workspace.
2. Under **OAuth & Permissions**, add these **Bot Token Scopes**:
   - `commands` — receive slash commands
   - `chat:write` — post confirmations and test messages
   - `users:read` — look up Slack users
   - `users:read.email` — match Slack profile email to TimeTracker accounts

3. Install the app to your workspace and copy the **Bot User OAuth Token** (`xoxb-…`).

### 2. Signing secret

Under **Basic Information**, copy the **Signing Secret**.

### 3. Slash commands

Under **Slash Commands**, create four commands. All should use the same **Request URL**:

```
https://your-timetracker-host/api/integrations/slack/attendance
```

| Command | Short description |
|---------|-------------------|
| `/in` | Clock in |
| `/brb` | Start break |
| `/back` | End break |
| `/out` | Clock out |

### 4. TimeTracker configuration

1. Log in as an administrator.
2. Go to **Integrations**.
3. In the **Workspace integrations** section, open **Slack Attendance**.
4. Enter the bot token, signing secret, and the **Attendance channel ID** (e.g. `C1234567890`).
5. Save and send a test message to verify the bot can post to the channel.

Invite the bot to the attendance channel if it is not already a member.

## Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/integrations/slack/attendance` | HMAC-SHA256 signature | Slash command handler for `/in`, `/brb`, `/back`, `/out`. |
| POST | `/api/integrations/slack-attendance/config` | Admin (`@login_required`) | Save bot token, signing secret, channel ID. |
| POST | `/api/integrations/slack-attendance/test` | Admin | Post a test message to the attendance channel. |
| GET | `/api/integrations/slack-attendance/status` | Admin | Connection state and config snapshot (no secrets). |

The webhook endpoint is `csrf.exempt` and rejects requests older than **5 minutes** or with an invalid `X-Slack-Signature`.

## User linking

TimeTracker resolves Slack users in this order:

1. **Slack user ID** stored on the TimeTracker user (`slack_user_id` column). Users can set this in **User Settings → Profile Information**.
2. **Email match** — if the Slack profile email matches the TimeTracker account email, the link is created automatically on first command.

## Attendance records

All clock-in events are recorded with `source=slack` in the attendance compliance system. Breaks and clock-outs follow the same rules as the web UI and mobile app.

## Zoho People / external HR systems

TimeTracker does not include a native Zoho People sync. Attendance data is available through the existing attendance API and compliance reports for export or custom integration.
