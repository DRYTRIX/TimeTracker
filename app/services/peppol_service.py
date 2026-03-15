import os
from typing import Optional, Tuple

from flask import current_app

from app import db
from app.integrations.peppol import PeppolParty, build_peppol_ubl_invoice_xml, peppol_enabled
from app.integrations.peppol_transport import GenericTransport, NativePeppolTransport, PeppolTransportError
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

    def send_invoice(
        self, invoice, triggered_by_user_id: Optional[int] = None
    ) -> Tuple[bool, Optional[InvoicePeppolTransmission], str]:
        if not peppol_enabled():
            return False, None, "Peppol is not enabled"

        try:
            sender = self._get_sender_party()
            recipient_party, recipient_endpoint_id, recipient_scheme_id = self._get_recipient_party(invoice)
        except Exception as e:
            return False, None, str(e)

        try:
            ubl_xml, sha256_hex = build_peppol_ubl_invoice_xml(
                invoice=invoice, supplier=sender, customer=recipient_party
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
                    (ap_token_raw or "").strip()
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
