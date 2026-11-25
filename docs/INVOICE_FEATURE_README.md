# Invoice Generation Feature - TimeTracker

## Overview

The Invoice Generation feature completes the billing workflow in TimeTracker: turn tracked time, expenses, and project costs into drafts, issue them, send them (email / Peppol / SDI), and track payment — with EN 16931-friendly line amounts and optional multi-entity seller/buyer details.

## Features

### Core invoice management
- **Two-step create** — **New invoice** opens step 1 at `/invoices/new` (`/invoices/create` redirects there with `project_id` / `client_id`): client, **Who bills whom**, period, projects, hours layout, expenses & costs, then **Create draft**
- **Draft page** — Hours lines with the time entries under each; edit lines in place; **Non-billable** / **×** per entry; expenses and project costs blocks; **Before you issue**; **Mark as issued**
- **Statuses** — Draft, **Issued**, Sent, Paid, Overdue, Cancelled (list filter for Issued)
- **Cancel and reissue** — Correct menu for issued/sent/overdue invoices without payments; or only cancel to return hours/costs to unbilled
- **Unique numbering** — Entity format (`{YYYY}` / `{YY}` / `{MM}` / `{DD}` / `{SEQ}`) or Settings; taken numbers refuse save with **Use next free**
- **Per-invoice currency** — Create/edit Currency select; defaults from the client's last invoice, else Settings

### Time, expenses, and costs
- **Show hours as** — One line per entry, by task, by person, by task and person, one line per project, or don't add hours; **Line description** template (`{date}`, `{project}`, `{task}`, `{person}`, `{note}`)
- **invoice_time_links** — Each billed entry is linked once to the line that bills it (prepaid-only coverage links without a line); edit/delete of linked entries is refused
- **Rates** — Per entry: user override → project override → project rate → client default
- **Expenses & project costs on step 1** — Period expenses/costs of selected projects, **Show costs as**, create draft bills the ticked ones; draft has Expenses and Project costs blocks
- **Project Invoices page** — `/projects/<id>/invoices` with New Invoice pre-filled for that project

### Legal entities and templates
- **Seller legal entities** (`billing_entities` module) — Admin → Legal entities; invoice **From / Currency / Pay to**; entity defaults and number format
- **Client legal entities** (`client_entities` module) — Client **Legal entities** card; invoice **Bill to** with buyer snapshot on the PDF
- **Invoice templates** — Admin → **Invoice templates**: **HTML templates** (Jinja + WeasyPrint) and **Visual layout** (Konva designer). Settings (and each entity) pick the default; Visual remains default until changed

### Financial & delivery
- Tax (header and per-line), discounts, line ordering
- Payment tracking (incl. Stripe / Mollie / PayPal)
- PDF export, email, Peppol/UBL, Factur-X/ZUGFeRD, XRechnung, FatturaPA/SDI
- Credit notes; reminder policies and recurring invoices — see [Invoice reminders and recurring](features/INVOICE_REMINDERS_AND_RECURRING.md)

## User interface

### Invoice list (`/invoices`)
Summary cards, filters (including **Issued**), export, bulk actions. Shared table also used on the project Invoices page.

### Step 1 (`/invoices/new`, `/invoices/<id>/step-1`)
Client, Who bills whom (From, Currency, Pay to, Bill to when modules are on), issue/due date, VAT, period (Last month / This month / Custom / All unbilled), projects with unbilled hours, **Show hours as** / **Line description**, expenses & costs, **Before you create**, then **Create draft** (or save on an existing draft's step 1). Summary refreshes via `POST /invoices/step-1/summary` without writing.

### Draft invoice (`/invoices/<id>`)
Header as printed; hours lines with entries underneath; **Add to matching lines** for new period entries; Notes/Terms; Preview PDF; **Mark as issued**; **Edit all fields** for the full form; `?view=full` for email/Peppol/approval/payments.

### Generate from Time (secondary)
Still available on a draft for adding or regrouping hours: same **Show hours as** / line template as step 1. API: `POST /api/v1/invoices/from-time-entries`, `POST /api/v1/invoices/{id}/generate-from-time` with optional `hours_layout` and `line_template`.

## Workflow

1. **Invoices → New invoice** — Complete step 1 and create the draft (or open a project's **Invoices → New Invoice**).
2. **Review the draft** — Adjust lines/entries, expenses, costs; fix anything listed under Before you issue.
3. **Mark as issued** — Locks lines/amounts and marks linked time as billed; then send (email / Peppol / SDI) or record payment.
4. **Corrections** — **Cancel and reissue** (copy to a new draft) or only cancel; use a credit note once there are payments.

## API (REST v1)

See [REST API — Invoices](api/REST_API.md#invoices-credit-notes-and-payments). Highlights:

- Create/update drafts; `currency_code` on list/detail
- `POST .../from-time-entries`, `POST .../{id}/generate-from-time` (`hours_layout`, `line_template`)
- `PUT .../{id}/items`; cancel/`DELETE` refuses invoices with payments (409)
- Linked time entries: edit/delete → 409 with invoice number; bulk skips `already_invoiced`

## Integration points

- **Projects / clients** — Rates, currency defaults, prepaid plans, legal entities
- **Time tracking** — Billable finished entries; badges **Billed** / **On draft** / **Non-billable** / **Marked paid**
- **Expenses & project costs** — Shared Expense categories; recurring costs
- **Settings / modules** — `invoices`, `billing_entities`, `client_entities`; Invoice Defaults (default template, VAT, terms)

## Configuration

- **Currency** — Global setting plus per-invoice (and Pay to account) currency
- **Rounding** — Entry hours rounded to 2 places before line totals
- **Number format** — Per legal entity or Settings
- **Default template** — Settings → Invoice Defaults; entity override when `billing_entities` is on

## Recurring invoices, reminders, and e-invoicing

- [Invoice reminders and recurring](features/INVOICE_REMINDERS_AND_RECURRING.md)
- [Peppol e-invoicing](admin/configuration/PEPPOL_EINVOICING.md) · [FatturaPA / SDI](admin/configuration/FATTURAPA_SDI.md)
- [Payment tracking](PAYMENT_TRACKING.md) · [Invoice expenses](INVOICE_EXPENSES.md) · [Project costs](features/PROJECT_COSTS_FEATURE.md)

## Troubleshooting

1. **Number already taken** — Use **Use next free** or pick another `{SEQ}`
2. **Entry missing from step 1 / Generate from Time** — Must be billable, finished, not already linked, and on a selected project (or client without project when allowed)
3. **Cannot edit a time entry** — It is on an invoice (draft or issued); remove it from the draft or cancel/reissue first
4. **Cannot cancel** — Invoice has payments; use Correct → Credit note

## Support

- In-app help and tooltips
- [REST API](api/REST_API.md) · [MCP sidecar](integrations/MCP.md)
- GitHub Issues / Discussions
