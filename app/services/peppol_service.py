import os
import re
import time
from typing import List, Optional, Tuple

from flask import current_app

from app import db
from app.integrations.peppol import (
    PeppolAttachment,
    PeppolParty,
    build_peppol_ubl_invoice_xml,
    peppol_enabled,
)
from app.integrations.peppol_transport import (
    GenericTransport,
    NativePeppolTransport,
    PeppolTransportError,
    PeppolTransportProtocol,
)
from app.models import InvoicePeppolTransmission, Settings
from app.utils.db import safe_commit


class PeppolService:
    """
    Business-level Peppol service:
    - reads config (env + client custom_fields)
    - generates UBL
    - sends via access point
    - persists send attempts for audit/retry
    """

    def __init__(self):
        # Result detail of the most recent send_invoice() call on this instance (routes
        # build one per request), so callers can report whether the PDF actually
        # travelled instead of assuming it did.
        self.last_pdf_status: str = "not_attempted"
        self.last_attachment_filenames: List[str] = []

    @staticmethod
    def embed_pdf_enabled() -> bool:
        """Whether the human-readable invoice PDF is embedded in the UBL (BG-24).

        Default on. Kill-switch for the case where an access point or a recipient
        chokes on embedded binaries: PEPPOL_EMBED_INVOICE_PDF=false.
        """
        return (os.getenv("PEPPOL_EMBED_INVOICE_PDF", "true") or "").strip().lower() in {
            "1", "true", "yes", "on",
        }

    def _build_pdf_attachment(self, invoice) -> Optional[PeppolAttachment]:
        """Render the invoice PDF for embedding as BT-125.

        Never raises: the UBL is the legal original and the PDF is a convenience copy, so
        a PDF problem degrades to a send without the attachment rather than blocking a
        valid invoice. Records the outcome in self.last_pdf_status
        (embedded | disabled | too_large | empty | error) so it can be reported.
        """
        if not self.embed_pdf_enabled():
            self.last_pdf_status = "disabled"
            return None

        try:
            from app.utils.pdf_generator import InvoicePDFGenerator

            pdf_bytes = InvoicePDFGenerator(invoice).generate_pdf()
        except Exception:
            current_app.logger.exception(
                "Peppol: invoice PDF generation failed; sending UBL without attachment"
            )
            self.last_pdf_status = "error"
            return None

        if not pdf_bytes:
            current_app.logger.warning("Peppol: invoice PDF generator returned no bytes")
            self.last_pdf_status = "empty"
            return None

        try:
            max_mb = float(os.getenv("PEPPOL_EMBED_PDF_MAX_MB", "5") or 5)
        except ValueError:
            max_mb = 5.0
        # Wire cost is roughly 1.85x the raw PDF: base64 inside the XML, and most access
        # points base64 the whole document again into their transport payload.
        if len(pdf_bytes) > max_mb * 1024 * 1024:
            current_app.logger.warning(
                "Peppol: invoice PDF is %.1f MB (cap %.1f MB); sending UBL without attachment",
                len(pdf_bytes) / 1024 / 1024, max_mb,
            )
            self.last_pdf_status = "too_large"
            return None

        number = (getattr(invoice, "invoice_number", None) or "").strip() or f"invoice-{getattr(invoice, 'id', '')}"
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", number).strip("-.") or "invoice"
        filename = f"{safe_name}.pdf"
        self.last_pdf_status = "embedded"
        self.last_attachment_filenames = [filename]
        return PeppolAttachment(
            document_id=number,
            filename=filename,
            mime_code="application/pdf",
            content=pdf_bytes,
            description="Commercial invoice (PDF)",
        )

    def _get_sender_party(self) -> PeppolParty:
        settings = Settings.get_settings()

        sender_endpoint_id = (
            getattr(settings, "peppol_sender_endpoint_id", "") or os.getenv("PEPPOL_SENDER_ENDPOINT_ID") or ""
        ).strip()
        sender_scheme_id = (
            getattr(settings, "peppol_sender_scheme_id", "") or os.getenv("PEPPOL_SENDER_SCHEME_ID") or ""
        ).strip()
        sender_country = (
            getattr(settings, "peppol_sender_country", "") or os.getenv("PEPPOL_SENDER_COUNTRY") or ""
        ).strip() or None

        if not sender_endpoint_id or not sender_scheme_id:
            raise ValueError("Missing PEPPOL_SENDER_ENDPOINT_ID / PEPPOL_SENDER_SCHEME_ID")

        return PeppolParty(
            endpoint_id=sender_endpoint_id,
            endpoint_scheme_id=sender_scheme_id,
            name=(getattr(settings, "company_name", None) or "Company").strip(),
            tax_id=(getattr(settings, "company_tax_id", None) or "").strip() or None,
            address_line=(getattr(settings, "company_address", None) or "").strip() or None,
            country_code=sender_country,
            email=(getattr(settings, "company_email", None) or "").strip() or None,
            phone=(getattr(settings, "company_phone", None) or "").strip() or None,
        )

    def _get_recipient_party(self, invoice) -> Tuple[PeppolParty, str, str]:
        client = getattr(invoice, "client", None)
        if not client:
            raise ValueError("Invoice has no linked client")

        # Store on Client.custom_fields to avoid schema changes on Client for now.
        endpoint_id = (client.get_custom_field("peppol_endpoint_id", "") or "").strip()
        scheme_id = (client.get_custom_field("peppol_scheme_id", "") or "").strip()
        country = (client.get_custom_field("peppol_country", "") or "").strip() or None

        if not endpoint_id or not scheme_id:
            raise ValueError(
                "Client is missing Peppol endpoint details (custom_fields.peppol_endpoint_id / peppol_scheme_id)"
            )

        party = PeppolParty(
            endpoint_id=endpoint_id,
            endpoint_scheme_id=scheme_id,
            name=(getattr(client, "name", None) or getattr(invoice, "client_name", "") or "Customer").strip(),
            tax_id=(client.get_custom_field("vat_id", "") or client.get_custom_field("tax_id", "") or "").strip()
            or None,
            address_line=(getattr(client, "address", None) or getattr(invoice, "client_address", None) or "").strip()
            or None,
            country_code=country,
            email=(getattr(client, "email", None) or getattr(invoice, "client_email", None) or "").strip() or None,
            phone=(getattr(client, "phone", None) or "").strip() or None,
        )
        return party, endpoint_id, scheme_id

    @staticmethod
    def _poll_ap_status(
        ap_url: str, ap_token: Optional[str], message_id: str,
        attempts: int = 4, delay_s: float = 4.0,
    ) -> Tuple[Optional[str], List[dict]]:
        """Poll the access-point adapter for the AP-side folder of an outbound message.

        Returns (folder lowercased or None, fatal_rules).
        Stops early on a terminal folder (sent/failed); never raises.
        """
        import requests

        base = (ap_url or "").strip().rstrip("/")
        if base.endswith("/send"):
            base = base[: -len("/send")]
        if not base:
            return None, []
        url = f"{base}/message/{message_id}/status"
        # The settings row can hold an empty access-point token (non-None), which wins
        # over the env var in the caller's resolution; the send transport falls back to
        # PEPPOL_ACCESS_POINT_TOKEN internally — mirror that here or status polls 401.
        if not ap_token:
            ap_token = (os.getenv("PEPPOL_ACCESS_POINT_TOKEN") or "").strip() or None
        headers = {"Authorization": f"Bearer {ap_token}"} if ap_token else {}
        folder: Optional[str] = None
        rules: List[dict] = []
        for i in range(max(1, attempts)):
            if i:
                time.sleep(delay_s)
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code >= 400:
                    continue
                data = resp.json() or {}
                folder = (data.get("folder") or "").strip().lower() or None
                rules = data.get("fatal_rules") or []
                if folder in {"sent", "failed"}:
                    break
            except Exception:
                continue
        return folder, rules

    def refresh_transmission_status(self, tx) -> dict:
        """One AP status check for an existing transmission; corrects tx.status when the
        AP reports failure after we recorded 'sent'."""
        if tx is None or not getattr(tx, "message_id", None):
            return {"folder": None, "fatal_rules": []}
        settings = Settings.get_settings()
        transport_mode = (
            (getattr(settings, "peppol_transport_mode", None) or os.getenv("PEPPOL_TRANSPORT_MODE") or "generic")
            .strip().lower()
        )
        if transport_mode == "native":
            return {"folder": None, "fatal_rules": []}
        ap_url = (
            getattr(settings, "peppol_access_point_url", "") or os.getenv("PEPPOL_ACCESS_POINT_URL") or ""
        ).strip()
        ap_token_raw = getattr(settings, "peppol_access_point_token", None)
        ap_token = (
            (settings.get_secret("peppol_access_point_token") or "").strip()
            if ap_token_raw is not None
            else (os.getenv("PEPPOL_ACCESS_POINT_TOKEN") or "").strip()
        )
        folder, rules = self._poll_ap_status(ap_url, ap_token or None, tx.message_id, attempts=1)
        if folder == "failed" and tx.status != "failed":
            reasons = "; ".join(
                f"[{r.get('id')}] {r.get('message')}" for r in (rules or [])[:6]
            ) or "access point reported delivery failure"
            tx.mark_failed(f"Access point validation/delivery failed: {reasons}")
            safe_commit("peppol_refresh_mark_failed", {"tx_id": tx.id})
        return {"folder": folder, "fatal_rules": rules}

    def send_invoice(
        self, invoice, triggered_by_user_id: Optional[int] = None
    ) -> Tuple[bool, Optional[InvoicePeppolTransmission], str]:
        self.last_pdf_status = "not_attempted"
        self.last_attachment_filenames = []
        if not peppol_enabled():
            return False, None, "Peppol is not enabled"

        try:
            sender = self._get_sender_party()
            recipient_party, recipient_endpoint_id, recipient_scheme_id = self._get_recipient_party(invoice)
        except Exception as e:
            return False, None, str(e)

        try:
            pdf_attachment = self._build_pdf_attachment(invoice)
            ubl_xml, sha256_hex = build_peppol_ubl_invoice_xml(
                invoice=invoice,
                supplier=sender,
                customer=recipient_party,
                attachments=[pdf_attachment] if pdf_attachment else None,
            )
        except Exception as e:
            current_app.logger.exception("Failed to build Peppol UBL XML")
            return False, None, f"Failed to build UBL XML: {e}"

        tx = InvoicePeppolTransmission(
            invoice_id=invoice.id,
            provider=(
                getattr(Settings.get_settings(), "peppol_provider", "") or os.getenv("PEPPOL_PROVIDER") or "generic"
            ).strip()
            or "generic",
            status="pending",
            sender_endpoint_id=sender.endpoint_id,
            sender_scheme_id=sender.endpoint_scheme_id,
            recipient_endpoint_id=recipient_endpoint_id,
            recipient_scheme_id=recipient_scheme_id,
            document_id=getattr(invoice, "invoice_number", None) or str(invoice.id),
            ubl_sha256=sha256_hex,
            ubl_xml=ubl_xml,
        )
        db.session.add(tx)
        if not safe_commit("peppol_create_transmission", {"invoice_id": invoice.id}):
            return False, None, "Database error while creating Peppol transmission"

        try:
            settings = Settings.get_settings()
            transport_mode = (
                (getattr(settings, "peppol_transport_mode", None) or os.getenv("PEPPOL_TRANSPORT_MODE") or "generic")
                .strip()
                .lower()
            )
            transport: PeppolTransportProtocol
            if transport_mode == "native":
                sml_url = (getattr(settings, "peppol_sml_url", "") or os.getenv("PEPPOL_SML_URL") or "").strip() or None
                cert_path = (
                    getattr(settings, "peppol_native_cert_path", "") or os.getenv("PEPPOL_NATIVE_CERT_PATH") or ""
                ).strip() or None
                key_path = (
                    getattr(settings, "peppol_native_key_path", "") or os.getenv("PEPPOL_NATIVE_KEY_PATH") or ""
                ).strip() or None
                try:
                    ap_timeout = int(getattr(settings, "peppol_access_point_timeout", 0) or 0) or 60
                except Exception:
                    ap_timeout = 60
                transport = NativePeppolTransport(
                    sml_url=sml_url, timeout_s=float(ap_timeout), cert_path=cert_path, key_path=key_path
                )
            else:
                ap_url = (
                    getattr(settings, "peppol_access_point_url", "") or os.getenv("PEPPOL_ACCESS_POINT_URL") or ""
                ).strip()
                ap_token_raw = getattr(settings, "peppol_access_point_token", None)
                ap_token = (
                    (settings.get_secret("peppol_access_point_token") or "").strip()
                    if ap_token_raw is not None
                    else (os.getenv("PEPPOL_ACCESS_POINT_TOKEN") or "").strip()
                )
                try:
                    ap_timeout = int(getattr(settings, "peppol_access_point_timeout", 0) or 0) or 30
                except Exception:
                    ap_timeout = 30
                transport = GenericTransport(
                    access_point_url=ap_url, access_point_token=ap_token or None, timeout_s=float(ap_timeout)
                )

            resp = transport.send(
                ubl_xml=ubl_xml,
                recipient_endpoint_id=recipient_endpoint_id,
                recipient_scheme_id=recipient_scheme_id,
                sender_endpoint_id=sender.endpoint_id,
                sender_scheme_id=sender.endpoint_scheme_id,
                document_id=tx.document_id,
            )

            message_id = None
            data = (resp or {}).get("data") or {}
            if isinstance(data, dict):
                message_id = data.get("message_id") or data.get("messageId") or data.get("id")

            tx.mark_sent(message_id=message_id, response_payload=resp)
            if not safe_commit("peppol_mark_sent", {"invoice_id": invoice.id, "tx_id": tx.id}):
                return True, tx, "Sent via Peppol, but failed to persist send status"

            # The AP accepts synchronously but validates/transmits async — poll briefly
            # so a validation failure doesn't masquerade as a successful send.
            verify = (os.getenv("PEPPOL_VERIFY_AFTER_SEND", "true").strip().lower()
                      in {"1", "true", "yes", "on"})
            if verify and message_id and transport_mode != "native":
                folder, fatal_rules = self._poll_ap_status(ap_url, ap_token or None, message_id)
                if folder == "failed":
                    reasons = "; ".join(
                        f"[{r.get('id')}] {r.get('message')}" for r in (fatal_rules or [])[:6]
                    ) or "access point reported delivery failure"
                    tx.mark_failed(f"Access point validation/delivery failed: {reasons}")
                    safe_commit("peppol_mark_failed", {"invoice_id": invoice.id, "tx_id": tx.id})
                    return False, tx, f"Peppol send FAILED at access point: {reasons}"
                if folder == "sent":
                    return True, tx, "Invoice sent via Peppol (access point confirmed transmission)"
                return True, tx, (
                    "Invoice accepted by access point; async validation/delivery still pending — "
                    "verify with the peppol-status endpoint before assuming delivery"
                )

            return True, tx, "Invoice sent via Peppol"
        except PeppolTransportError as e:
            tx.mark_failed(str(e))
            safe_commit("peppol_mark_failed", {"invoice_id": invoice.id, "tx_id": tx.id})
            current_app.logger.exception("Peppol send failed")
            return False, tx, f"Peppol send failed: {e}"
        except Exception as e:
            tx.mark_failed(str(e))
            safe_commit("peppol_mark_failed", {"invoice_id": invoice.id, "tx_id": tx.id})
            current_app.logger.exception("Peppol send failed")
            return False, tx, f"Peppol send failed: {e}"
