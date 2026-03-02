# Peppol and ZugFerd e-invoicing (EN 16931)

TimeTracker supports **both**:

- **Peppol** – send invoices via the Peppol network (UBL 2.1, BIS Billing 3.0) to your **Peppol Access Point**.
- **ZugFerd / Factur-X** – export invoice PDFs that contain **embedded EN 16931 XML** (one file that is both human-readable and machine-readable). These hybrid PDFs can also be sent via Peppol.

Peppol is the **transport**; ZugFerd is a **format** (PDF + embedded XML). The same UBL used for Peppol is reused when embedding (EN 16931 compliant).

## What you need

- **A Peppol Access Point provider** (e.g. your accountant’s solution or a commercial AP)
- Your **sender identifiers** (how your company is identified in Peppol)
- Your customers’ **recipient endpoint identifiers**

TimeTracker supports two **transport modes**:

- **Generic** – provider-agnostic HTTP adapter: you configure an access point URL that accepts the JSON contract below. No SML/SMP or AS4 required.
- **Native** – SML/SMP participant discovery and AS4 message send. Requires `PEPPOL_SML_URL` (and optionally client certificate paths for mTLS). Use when you want to send directly via the PEPPOL network without a third-party AP adapter.

Sender and recipient identifiers are validated (scheme and endpoint ID format) before send in both modes.

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
- **`PEPPOL_TRANSPORT_MODE`** (optional): `generic` or `native` (default: `generic`)
- **`PEPPOL_SML_URL`** (required for native): SML directory URL (e.g. EU directory)
- **`PEPPOL_NATIVE_CERT_PATH`** / **`PEPPOL_NATIVE_KEY_PATH`** (optional): client certificate and key for AS4 mTLS

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

## Make all invoices PEPPOL compliant

In **Admin → Settings → Peppol e-Invoicing** you can enable **Make all invoices PEPPOL compliant**. When this is on:

- **PDFs** include PEPPOL/EN 16931 identifiers (seller and buyer endpoint and VAT) where configured.
- **Invoice view** shows warnings when required data is missing (company Tax ID, sender Endpoint/Scheme ID, or client `peppol_endpoint_id` / `peppol_scheme_id`).
- **UBL** generated for Peppol includes mandatory BIS Billing 3.0 elements: `InvoiceTypeCode` (380) and `BuyerReference` (from invoice, project name, or invoice number).

You can optionally set **Buyer reference (PEPPOL BT-10)** on each invoice (create/edit). If left empty, the UBL uses the project name or invoice number.

When the setting is on **and** the client has Peppol endpoint details, the invoice view shows a **Download UBL** button to save the UBL 2.1 XML file.

## Embed EN 16931 XML in invoice PDFs (ZugFerd / Factur-X)

In **Admin → Settings → Peppol e-Invoicing** you can enable **Embed EN 16931 XML in invoice PDFs (ZugFerd / Factur-X)**. When this is on:

- **Exported invoice PDFs** (Export PDF) contain an embedded file `ZUGFeRD-invoice.xml` with the same EN 16931 UBL as used for Peppol.
- The embedded XML is attached as an **Associated File** with relationship **Alternative**, and ZUGFeRD XMP RDF is written (metadata is created if missing so validators recognize the document).
- The PDF remains human-readable; the embedded XML makes it machine-readable (e.g. for automated booking or archiving).
- These hybrid PDFs can be sent via Peppol or by email; recipients can open the PDF and/or extract the XML.
- **Strict behaviour:** If ZUGFeRD embedding is enabled and the embed step fails (e.g. missing pikepdf, invalid PDF), the export is **aborted** and the user sees an error; the PDF is not returned without the XML.

Party data (seller/customer) is taken from Settings and the invoice’s client (including Peppol endpoint fields). For full EN 16931/ZugFerd compliance, configure sender and client data as for Peppol (including company and client addresses and country codes).

**Validation:** Validate the embedded XML with [b2brouter](https://app.b2brouter.net/de/validation) or [portinvoice.com](https://www.portinvoice.com/). You can optionally enable **Run veraPDF after export** in Admin → Peppol e-Invoicing and set the veraPDF executable path to get a validation summary after each export (does not block the download).

### ZUGFeRD and PDF/A-3

You can enable **Normalize ZUGFeRD PDFs to PDF/A-3** in Admin → Peppol e-Invoicing. When this is on (and ZUGFeRD embedding is enabled), exported PDFs are normalized to PDF/A-3: XMP identification (pdfaid part 3, conformance B) and an sRGB output intent are added so the file passes validators such as veraPDF. If conversion fails, export is aborted and the user sees an error.

## Migrations

After pulling these changes, run:

```bash
flask db upgrade
```

This applies (among others):

- `112_add_invoices_peppol_compliant` (adds `settings.invoices_peppol_compliant`)
- `113_add_invoice_buyer_reference` (adds `invoices.buyer_reference`)
- `128_add_invoices_zugferd_pdf` (adds `settings.invoices_zugferd_pdf` for ZugFerd PDF embedding)
- `130_add_peppol_transport_mode_and_native` (adds `peppol_transport_mode`, `peppol_sml_url`, `peppol_native_cert_path`, `peppol_native_key_path`, `invoices_pdfa3_compliant`, `invoices_validate_export`, `invoices_verapdf_path`)

## Testing

With your virtual environment activated:

```bash
pytest tests/test_peppol_service.py tests/test_peppol_identifiers.py tests/test_zugferd.py tests/test_pdfa3.py tests/test_invoice_validators.py -v
```

