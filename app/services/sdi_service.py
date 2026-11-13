"""Italian SDI (FatturaPA) transmission service."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple

from flask import current_app

from app import db
from app.integrations.sdi_transport import GenericSdiTransport, SdiTransportError
from app.models import InvoiceSdiTransmission, Settings
from app.models.invoice_sdi import SDI_FINAL_STATUSES
from app.utils.db import safe_commit
from app.utils.fatturapa import (
    build_fatturapa_xml,
    determine_formato,
    progressivo_from_id,
    resolve_codice_destinatario,
    validate_fatturapa_ready,
)

logger = logging.getLogger(__name__)


class SdiService:
    """Build FatturaPA XML and send via a configured SDI intermediary."""

    def _transport(self, settings: Any) -> GenericSdiTransport:
        url = (getattr(settings, "sdi_transport_url", "") or "").strip()
        token = ""
        try:
            token = (settings.get_secret("sdi_transport_token") or "").strip()
        except Exception:
            token = (getattr(settings, "sdi_transport_token", "") or "").strip()
        try:
            timeout = int(getattr(settings, "sdi_timeout", 0) or 0) or 30
        except Exception:
            timeout = 30
        return GenericSdiTransport(url=url, token=token or None, timeout=timeout)

    def send_invoice(
        self, invoice, triggered_by_user_id: Optional[int] = None
    ) -> Tuple[bool, Optional[InvoiceSdiTransmission], str]:
        settings = Settings.get_settings()
        if not bool(getattr(settings, "sdi_enabled", False)):
            return False, None, "SDI is not enabled"

        client = getattr(invoice, "client", None)
        errors = validate_fatturapa_ready(invoice, settings, client)
        if errors:
            return False, None, "; ".join(errors)

        if not (getattr(settings, "sdi_transport_url", "") or "").strip():
            return False, None, "SDI transport URL is not configured"

        formato = determine_formato(client)
        codice_dest, pec = resolve_codice_destinatario(client)

        tx = InvoiceSdiTransmission(
            invoice_id=invoice.id,
            status="pending",
            formato=formato,
            progressivo="",  # filled after we have an id
        )
        db.session.add(tx)
        if not safe_commit("sdi_create_transmission", {"invoice_id": invoice.id}):
            return False, None, "Database error while creating SDI transmission"

        progressivo = progressivo_from_id(tx.id)
        try:
            xml, filename, sha256_hex = build_fatturapa_xml(invoice, settings, client, progressivo)
        except Exception:
            current_app.logger.exception("Failed to build FatturaPA XML")
            tx.mark_failed("Failed to build FatturaPA XML")
            safe_commit("sdi_mark_failed_build", {"invoice_id": invoice.id, "tx_id": tx.id})
            return False, tx, "Failed to build FatturaPA XML"

        tx.progressivo = progressivo
        tx.filename = filename
        tx.xml = xml
        tx.xml_sha256 = sha256_hex
        safe_commit("sdi_store_xml", {"invoice_id": invoice.id, "tx_id": tx.id})

        try:
            transport = self._transport(settings)
            resp = transport.send(
                filename=filename,
                formato=formato,
                codice_destinatario=codice_dest,
                pec=pec,
                xml=xml,
                sha256=sha256_hex,
            )
            message_id = resp.get("message_id") or resp.get("messageId") or resp.get("id")
            sdi_id = resp.get("sdi_identifier") or resp.get("sdiIdentifier")
            tx.mark_sent(message_id=message_id, sdi_identifier=sdi_id, response_payload=resp)
            if not safe_commit("sdi_mark_sent", {"invoice_id": invoice.id, "tx_id": tx.id}):
                return True, tx, "Sent via SDI, but failed to persist send status"
            return True, tx, "Invoice sent via SDI"
        except SdiTransportError as e:
            # Persist detail on the transmission; return a generic client message.
            tx.mark_failed(str(e))
            safe_commit("sdi_mark_failed", {"invoice_id": invoice.id, "tx_id": tx.id})
            current_app.logger.exception("SDI send failed")
            return False, tx, "SDI send failed"
        except Exception as e:
            tx.mark_failed(type(e).__name__)
            safe_commit("sdi_mark_failed", {"invoice_id": invoice.id, "tx_id": tx.id})
            current_app.logger.exception("SDI send failed")
            return False, tx, "SDI send failed"

    def refresh_status(self, tx: InvoiceSdiTransmission) -> dict:
        """Poll intermediary for status and apply notifications."""
        if not tx.message_id:
            return {"ok": False, "error": "No message_id on transmission"}
        if tx.status in SDI_FINAL_STATUSES:
            return {"ok": True, "status": tx.status, "skipped": True}

        settings = Settings.get_settings()
        try:
            transport = self._transport(settings)
            data = transport.get_status(tx.message_id)
        except SdiTransportError as e:
            current_app.logger.warning("SDI status refresh transport error: %s", e)
            return {"ok": False, "error": "SDI status refresh failed"}
        except Exception:
            current_app.logger.exception("SDI status refresh failed")
            return {"ok": False, "error": "SDI status refresh failed"}

        sdi_id = data.get("sdi_identifier") or data.get("sdiIdentifier")
        if sdi_id:
            tx.sdi_identifier = str(sdi_id)

        notifications = data.get("notifications") or []
        if isinstance(notifications, list):
            for n in notifications:
                if not isinstance(n, dict):
                    continue
                ntype = n.get("type") or n.get("Tipo") or ""
                # Avoid re-applying identical notification types already stored
                existing = {(x.get("type") or "").upper() for x in (tx.notifications or []) if isinstance(x, dict)}
                if str(ntype).upper() in existing and str(ntype).upper() not in ("NE",):
                    # Still allow NE updates; skip exact duplicate types for others
                    continue
                tx.apply_notification(ntype, detail=n.get("detail") or n.get("Descrizione"), date=n.get("date"))

        # Fallback: intermediary may return a top-level status string
        top_status = (data.get("status") or "").strip().lower()
        if top_status and top_status in {
            "sent",
            "delivered",
            "not_delivered",
            "rejected",
            "accepted",
            "refused",
            "expired",
            "failed",
            "pending",
        }:
            # Only upgrade if we didn't get richer notification mapping
            if not notifications:
                tx.status = top_status
                tx.updated_at = datetime.utcnow()

        safe_commit("sdi_refresh_status", {"tx_id": tx.id})
        return {"ok": True, "status": tx.status, "data": data}

    def poll_pending(self, max_age_days: int = 30) -> int:
        """Refresh non-final transmissions newer than max_age_days. Returns count refreshed."""
        settings = Settings.get_settings()
        if not bool(getattr(settings, "sdi_enabled", False)):
            return 0
        if not (getattr(settings, "sdi_transport_url", "") or "").strip():
            return 0

        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        pending: List[InvoiceSdiTransmission] = (
            InvoiceSdiTransmission.query.filter(
                InvoiceSdiTransmission.status.notin_(list(SDI_FINAL_STATUSES)),
                InvoiceSdiTransmission.created_at >= cutoff,
                InvoiceSdiTransmission.message_id.isnot(None),
            )
            .order_by(InvoiceSdiTransmission.created_at.asc())
            .limit(100)
            .all()
        )
        count = 0
        for tx in pending:
            result = self.refresh_status(tx)
            if result.get("ok"):
                count += 1
        return count
