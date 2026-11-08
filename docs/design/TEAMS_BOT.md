# Microsoft Teams bot — slash command parity with Slack `/tt`

Slack integration (`app/integrations/slack_connector.py`) supports **`/tt`** subcommands: `start`, `stop`, `status`, `today`. Microsoft Teams uses `MicrosoftTeamsConnector` for OAuth, channel notifications, Graph API messaging, and interactive bot commands.

## Status (implemented)

- Shared command logic lives in `app/services/chat_command_service.py` (`handle_timer_command`).
- Slack `/tt` and Teams bot both call that service.
- Route: `POST /api/integrations/teams/bot/messages` validates Bot Framework JWT (PyJWT + cached JWKS from `login.botframework.com`) when possible; requires `Authorization: Bearer` at minimum. Set `MICROSOFT_TEAMS_BOT_APP_ID` (or `MICROSOFT_TEAMS_CLIENT_ID`) for audience verification.
- User resolution: activity `from.email` / UPN → `User.email`, or `linked_teams_user_id` on the integration config.
- Replies: plain text + Adaptive Card attachment.

## Goal

Provide the **same timer operations** from Teams via:

1. **Message extension / slash command** (Bot Framework), or  
2. **Adaptive Card actions** in a dedicated chat tab (phase 2).

## Parity matrix

| Slack `/tt` | Teams (target) | Notes |
|-------------|----------------|-------|
| `start [project]` | `@TimeTracker start [project]` or `/tt start` | Resolve project by id/name like Slack |
| `stop` | `stop` | Stop active timer for linked user |
| `status` | `status` | Ephemeral reply with current timer |
| `today` | `today` | Hours summary via notification service |
| (help) | empty command | List subcommands |

## Identity linking

| Slack | Teams |
|-------|-------|
| `User.slack_user_id` / `linked_slack_user_id` | `linked_teams_user_id` in integration config, or email match |

Match incoming activity `from.aadObjectId` / email to TimeTracker user.

## Architecture

```text
Teams client → Azure Bot Service → POST /api/integrations/teams/bot/messages
                                              ↓
                              MicrosoftTeamsConnector.handle_bot_command()
                                              ↓
                              chat_command_service → TimeTrackingService
```

### Azure resources (setup checklist)

- Bot registration in Azure Portal (App ID + secret).
- Messaging endpoint: `{APP_BASE_URL}/api/integrations/teams/bot/messages`.
- Teams channel enabled for the bot.
- Optional: single-tenant vs multi-tenant bot (align with `microsoft_teams_tenant_id`).

## Security

- Validate Bot Framework **JWT** on each activity (`Authorization: Bearer`).
- Do not trust `from.id` without mapping to a TimeTracker user.
- Rate-limit per `conversation.id` (follow-up).

## Follow-ups

- Stronger multi-tenant audience checks and proactive Graph replies.
- User settings UI to link Teams AAD object id.

## References

- `docs/integrations/SLACK.md`
- `app/integrations/microsoft_teams.py`
- `app/integrations/slack_connector.py`
- `app/services/chat_command_service.py`
