# FatturaPA and SDI (Italy)

TimeTracker can generate **FatturaPA 1.2 XML** (B2B `FPR12` and public administration `FPA12`) and optionally send it to the Italian **Sistema di Interscambio (SDI)** through your accredited intermediary.

Digital signature (`.p7m`) and inbound purchase invoices are out of scope; intermediaries typically sign on your behalf.

## What you need

1. **Company branding** (Admin → Settings):
   - Partita IVA (`company_tax_id`, e.g. `IT01234567890`) and/or Codice Fiscale
   - Structured address: street, CAP, city, provincia, country `IT`
   - Regime fiscale (default `RF01`)
   - IBAN (for payment details in the XML)
2. **Client** fields:
   - VAT ID or Codice Fiscale
   - Structured address + provincia (for Italian buyers)
   - **SDI Codice Destinatario** (7 chars B2B / 6 chars PA) **or** PEC email
3. Optional on the invoice: **CIG** / **CUP** for public-administration procurement

## Export

On the invoice page, use **Download FatturaPA**. The file name follows the SDI convention:

`IT{IdTrasmittente}_{ProgressivoInvio}.xml`

Missing mandatory fields return HTTP 400 with a JSON list of readiness messages (same pattern as XRechnung).

## Send via SDI

1. Enable **SDI sending** under Admin → Settings → **SDI / FatturaPA**.
2. Set the **intermediary URL** (typically ending in `/send`) and optional bearer token.
3. On the invoice page, click **Send via SDI**.

Transmissions are stored with status `pending` → `sent`, then updated from SDI notifications (`RC`, `NS`, `MC`, `NE`, `DT`, `AT`) via:

- Manual **Refresh** on the invoice history table
- Scheduled job `poll_sdi_status` every 15 minutes (non-final transmissions younger than 30 days)

API twin: `POST /api/v1/invoices/<id>/send-sdi` (scope `write:invoices`).

## Generic intermediary HTTP contract

TimeTracker talks to a **generic HTTP adapter** you configure (your own microservice, or a thin wrapper around Aruba / A-Cube / Openapi / etc.).

### Send

`POST {sdi_transport_url}`

```http
Authorization: Bearer {token}
Content-Type: application/json
```

```json
{
  "filename": "IT01234567890_00001.xml",
  "formato": "FPR12",
  "recipient": {
    "codice_destinatario": "ABC1234",
    "pec": null
  },
  "xml_base64": "<base64 of UTF-8 XML>",
  "sha256": "<hex sha256 of the XML bytes>"
}
```

Expected response:

```json
{
  "message_id": "provider-message-id",
  "sdi_identifier": "optional-sdi-id"
}
```

### Status

`GET {base}/message/{message_id}/status`  
(`base` is the transport URL with a trailing `/send` removed)

```json
{
  "status": "delivered",
  "sdi_identifier": "optional",
  "notifications": [
    { "type": "RC", "date": "2026-11-08T10:00:00Z", "detail": "ok" }
  ]
}
```

Notification types map to transmission status:

| Type | Status |
|------|--------|
| RC | delivered |
| NS | rejected |
| MC | not_delivered (still legally issued) |
| NE | accepted or refused (from detail text) |
| DT | expired |
| AT | failed |

## Recipient rules

| Situation | Codice Destinatario | Notes |
|-----------|---------------------|-------|
| B2B with SDI code | 7 characters | `FPR12` |
| Public administration | 6 characters | `FPA12`; set CIG/CUP when required |
| B2B with PEC only | `0000000` | PECDestinatario is set |
| Foreign buyer | `XXXXXXX` | CAP forced to `00000` |

## Related

- [Peppol / Factur-X / ZUGFeRD](PEPPOL_EINVOICING.md) — EN 16931 UBL/CII formats (different schema from FatturaPA)
- [Peppol Bridge](PEPPOL_BRIDGE.md) — similar adapter pattern for Peppol
