# Xero Integration

TimeTracker can sync invoices, expenses, and payments with [Xero](https://www.xero.com/) via the Xero Accounting API and OAuth 2.0.

## Requirements

- A [Xero Developer](https://developer.xero.com/) app (Client ID and Client Secret).
- For apps **created on or after March 2, 2026**, the integration uses the granular accounting scopes required by Xero; older apps continue to work until broad scopes are retired (see [Xero scope changes](https://developer.xero.com/documentation/guides/oauth2/scopes/)).

## OAuth scopes

The integration requests the following scopes:

| Scope | Purpose |
|-------|---------|
| `accounting.invoices` | Invoices, credit notes, purchase orders, quotes, items |
| `accounting.payments` | Payments, batch payments, overpayments, prepayments |
| `accounting.contacts` | Contacts |
| `accounting.settings` | Organisation and account settings |
| `offline_access` | Refresh token for background sync |

**Note:** The deprecated scope `accounting.transactions` is no longer used. For apps created on or after March 2, 2026, Xero requires the granular scopes above (see [Issue #567](https://github.com/DRYTRIX/TimeTracker/issues/567)).

## Setup

1. In [Xero Developer](https://developer.xero.com/app/manage), create an app (or use an existing one) and note the **Client ID** and **Client Secret**.
2. Set the app **Redirect URI** to your TimeTracker base URL plus `/integrations/xero/callback` (e.g. `https://your-timetracker.example.com/integrations/xero/callback`).
3. In TimeTracker: **Integrations** → **Xero** → complete the setup wizard with your Client ID and Client Secret.
4. Open **Connect** (or go to `/integrations/xero/connect`) to start the OAuth flow. Sign in to Xero, select the organisation, and authorise. You are redirected back with the connection stored.

## Configuration

- **Tenant ID** — Set automatically during OAuth; you can also enter it manually if needed.
- **Sync direction** — Xero → TimeTracker (import), TimeTracker → Xero (export), or bidirectional.
- **Items to sync** — Invoices, expenses, payments, contacts.
- **Data mapping** — Contact mappings (clients → Xero contacts), item mappings (invoice items → Xero items), account mappings (expense categories → Xero account codes), and default expense account code.

## Sync behaviour

- **Invoices** — Pushed to Xero as sales invoices via `POST /api.xro/2.0/Invoices`. Response `InvoiceID` is stored in invoice metadata as `xero_invoice_id`.
- **Expenses** — Pushed to Xero as expense claims via `POST /api.xro/2.0/ExpenseClaims`. Response `ExpenseClaimID` is stored in expense metadata as `xero_expense_id`. The Xero ExpenseClaims API expects a specific payload shape (e.g. User and Receipts); if you see validation errors, the payload may need to be adapted to your Xero app and workflow.
- **Manual sync** — Use **Sync Now** on the integration page.
- **Auto sync** — Enable in setup and choose a schedule (e.g. hourly, daily).

## Troubleshooting

- **"Invalid scope for client"** — Ensure you are using TimeTracker with the updated scopes (`accounting.invoices`, `accounting.payments`, etc.). Re-create your Xero app or use an app created before March 2, 2026 if you must use the old broad scope during the transition.
- **404 on expense sync** — The integration uses `/api.xro/2.0/ExpenseClaims`; the previous `/api.xro/2.0/Expenses` endpoint does not exist in the Xero API.
- **Connection test** — Use the integration’s connection test to verify tenant and token; fix any credential or tenant ID issues before syncing.
