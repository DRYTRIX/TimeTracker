# Microsoft Teams bot — slash command parity with Slack `/tt`

Slack integration (`app/integrations/slack_connector.py`) supports **`/tt`** subcommands: `start`, `stop`, `status`, `today`. Microsoft Teams today uses `MicrosoftTeamsConnector` for OAuth, channel notifications, and Graph API messaging—not interactive bot commands.

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

| Slack | Teams (proposed) |
|-------|------------------|
| `User.slack_user_id` | New `User.teams_aad_id` or store in integration config `linked_teams_user_id` |
| Per-integration `linked_slack_user_id` | Per-integration `linked_teams_user_id` |

Match incoming activity `from.aadObjectId` to TimeTracker user.

## Architecture

```text
Teams client → Azure Bot Service → POST /api/integrations/teams/bot/messages
                                              ↓
                              MicrosoftTeamsConnector.handle_bot_command()
                                              ↓
                              TimeTrackingService (same as Slack)
```

### Azure resources (setup checklist)

- Bot registration in Azure Portal (App ID + secret).
- Messaging endpoint: `{APP_BASE_URL}/api/integrations/teams/bot/messages`.
- Teams channel enabled for the bot.
- Optional: single-tenant vs multi-tenant bot (align with `microsoft_teams_tenant_id`).

## Stub (current)

- `MicrosoftTeamsConnector.handle_bot_command()` returns **501** with a short message pointing to this doc.
- Route: `POST /api/integrations/teams/bot/messages` in `app/routes/integrations_webhooks.py` (JSON body placeholder; Bot Framework JWT validation in phase 2).

## Security (implementation)

- Validate Bot Framework **JWT** on each activity (`Authorization: Bearer`).
- Do not trust `from.id` without mapping to a TimeTracker user.
- Rate-limit per `conversation.id`.

## Implementation phases

1. Stub route + handler (this phase).
2. Bot Framework auth + user linking UI in user settings.
3. Implement subcommands reusing Slack private methods (shared `ChatTimerCommandMixin` optional refactor).
4. Proactive notifications (already partial via Graph `send_message`).

## References

- `docs/integrations/SLACK.md`
- `app/integrations/microsoft_teams.py`
- `app/integrations/slack_connector.py`
