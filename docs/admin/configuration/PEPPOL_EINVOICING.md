# Peppol e-invoicing (BIS Billing 3.0)

TimeTracker can **send invoices via Peppol** by generating a UBL 2.1 Invoice (Peppol BIS Billing 3.0 profile) and forwarding it to your **Peppol Access Point**.

## What you need

- **A Peppol Access Point provider** (e.g. your accountant’s solution or a commercial AP)
- Your **sender identifiers** (how your company is identified in Peppol)
- Your customers’ **recipient endpoint identifiers**

TimeTracker intentionally ships with a **provider-agnostic HTTP adapter**, so you can connect to any access point by exposing (or configuring) an HTTP endpoint that accepts the JSON contract described below.

## Enable Peppol

You can enable Peppol either:

- via **Admin → System Settings → Peppol e-Invoicing**, or
- via environment variables (see `env.example`).

Environment variables:

- **`PEPPOL_ENABLED=true`**
- **`PEPPOL_SENDER_ENDPOINT_ID`**: your company endpoint id (value depends on scheme/country/provider)
- **`PEPPOL_SENDER_SCHEME_ID`**: the scheme id for the sender endpoint
- **`PEPPOL_ACCESS_POINT_URL`**: the URL of your access point adapter endpoint
- **`PEPPOL_ACCESS_POINT_TOKEN`** (optional): bearer token used by the adapter
- **`PEPPOL_ACCESS_POINT_TIMEOUT`** (optional): request timeout seconds (default: 30)
- **`PEPPOL_PROVIDER`** (optional): label stored in send history (default: `generic`)

## Set recipient Peppol endpoint on a client

For now, recipient endpoint details are stored on the `Client` using `custom_fields`:

- **`peppol_endpoint_id`**: the recipient endpoint identifier
- **`peppol_scheme_id`**: the recipient scheme identifier
- **`peppol_country`** (optional): 2-letter country code (e.g. `BE`)

When both `peppol_endpoint_id` and `peppol_scheme_id` are present, the invoice page will enable **Send via Peppol**.

## Sending an invoice

On an invoice page, click **Send via Peppol**. Each attempt is stored in:

- `invoice_peppol_transmissions` (status: `pending` → `sent` or `failed`)

The invoice page shows a **Peppol History** table (for auditing and troubleshooting).

## Access Point adapter contract

TimeTracker sends a POST request like:

```json
{
  "recipient": { "endpoint_id": "…", "scheme_id": "…" },
  "sender": { "endpoint_id": "…", "scheme_id": "…" },
  "document": {
    "id": "INV-…",
    "type_id": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##…::2.1",
    "process_id": "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"
  },
  "payload": { "ubl_xml": "<?xml version=\"1.0\" …>…</Invoice>" }
}
```

Your adapter should:

- forward the UBL to your access point provider API
- return JSON (recommended) with a message id, for example:

```json
{ "message_id": "…" }
```

If the adapter returns HTTP \(\ge 400\), TimeTracker marks the attempt as **failed** and stores the error.

