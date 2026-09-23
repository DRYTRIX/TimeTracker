# Zapier & Make (Integromat) integration via webhooks

TimeTracker already supports **outbound webhooks** (`Webhook` model, `WebhookDispatcher`, `WebhookEvent` in `app/constants.py`). Zapier and Make do not need native SDKs for most automations: they consume **HTTPS webhook payloads** and call the **REST API** for actions.

This document describes trigger/action mapping for no-code platforms using existing infrastructure.

## Architecture

```text
TimeTracker event → WebhookDispatcher → POST JSON → Zapier Catch Hook / Make Custom Webhook
                                                              ↓
                                                    Filter / transform
                                                              ↓
                              Make/Zapier → TimeTracker REST API (ApiToken Bearer)
```

## Outbound triggers (TimeTracker → Zapier/Make)

Configure in **Admin → Webhooks** (or API). Subscribe to event types from `WebhookEvent`:

| Webhook event | Typical automation |
|---------------|-------------------|
| `time_entry.created` | Log row in Google Sheets, notify Slack channel |
| `time_entry.updated` | Sync to project management tool |
| `project.created` | Create folder in Drive, notify PM |
| `invoice.sent` | Accounting pipeline, email finance |
| `invoice.paid` | Close deal in CRM, thank-you email |
| `task.created` | Create card in Trello/Asana (via their Zapier apps) |
| `integration.error` | PagerDuty / email ops |

Payload shape (simplified):

```json
{
  "event": "time_entry.created",
  "timestamp": "2026-09-23T12:00:00Z",
  "data": {
    "time_entry_id": 123,
    "project_id": 45,
    "user_id": 7
  }
}
```

HMAC signature: webhook `secret` → `X-TimeTracker-Signature` (see `Webhook.sign_payload` in `app/models/webhook.py`).

### Sample Zap (Zapier)

1. **Trigger:** Webhooks by Zapier → Catch Hook.
2. Copy hook URL into TimeTracker webhook `url`.
3. Subscribe to `time_entry.created` (and optionally `time_entry.updated`).
4. **Filter:** Only continue if `data.project_id` matches a known client project (optional).
5. **Action:** Google Sheets → Create Spreadsheet Row  
   - Map `data.time_entry_id`, fetch details via Zapier “Webhooks by Zapier → GET” to `{base}/api/v1/time-entries/{id}` with `Authorization: Bearer tt_…`.

### Sample scenario (Make)

1. **Custom webhook** module receives TimeTracker POST.
2. **Router** on `event` field:
   - `invoice.paid` → QuickBooks module (or TimeTracker API to mark external ref).
   - `time_entry.created` → Slack module message with duration (after HTTP GET entry).
3. **HTTP module** for API calls using stored API token connection.

## Inbound actions (Zapier/Make → TimeTracker)

Use **REST API v1** with scoped `ApiToken`:

| Automation need | API |
|-----------------|-----|
| Start/stop timer | `POST /api/v1/time-entries` (or timer endpoints if exposed) |
| Create project | `POST /api/v1/projects` |
| Create client | `POST /api/v1/clients` |
| List entries for reporting | `GET /api/v1/time-entries?...` |

Document base URL: `{APP_BASE_URL}/api/v1/…`.

## Recommended webhook subscriptions by use case

| Use case | Events |
|----------|--------|
| Daily timesheet backup | `time_entry.created`, `time_entry.updated` |
| Invoice AR workflow | `invoice.sent`, `invoice.paid` |
| Project kickoff | `project.created`, `task.created` |
| Integration health | `integration.error` |

## Future enhancements (not required for webhook-based Zaps)

- Official Zapier app with OAuth2 (see `docs/design/OAUTH2_API_APPS.md`).
- Pre-built Make app manifest.
- Polling triggers for accounts that cannot expose inbound URLs (use API + scheduled Make scenario).

## Testing

1. Admin → Webhooks → Test delivery (`webhook.test` event).
2. Use [webhook.site](https://webhook.site) or Zapier catch hook to inspect JSON + signature headers.
3. Verify API token scopes match actions (`write:time_entries`, etc.).

## References

- `app/models/webhook.py`, `app/utils/webhook_dispatcher.py`, `app/constants.WebhookEvent`
- `docs/api/REST_API.md`
