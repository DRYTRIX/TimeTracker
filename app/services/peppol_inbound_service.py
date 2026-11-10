"""Poll Peppol Bridge inbox and store inbound UBL documents."""

from __future__ import annotations

import hashlib
import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

import requests

from app import db
from app.models import Client, PeppolInboundDocument, Settings
from app.utils.db import safe_commit

logger = logging.getLogger(__name__)

_UBL_NS = {
    "inv": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cn": "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}


def _bool_setting(settings: Settings, attr: str, default: bool = False) -> bool:
    val = getattr(settings, attr, None)
    if val is None:
        return default
    return bool(val)


def bridge_base_url_from_access_point(access_point_url: str) -> Optional[str]:
    """Derive bridge base (… without /send) from PEPPOL_ACCESS_POINT_URL."""
    url = (access_point_url or "").strip()
    if not url:
        return None
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return None
    path = (parts.path or "").rstrip("/")
    if path.endswith("/send"):
        path = path[: -len("/send")]
    return urlunsplit((parts.scheme, parts.netloc, path, "", "")).rstrip("/")


def _sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text[:10] if fmt == "%Y-%m-%d" else text[:8], fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(value: Optional[str]) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None


def _local_tag(tag: str) -> str:
    if not tag:
        return ""
    return tag.split("}")[-1]


def parse_ubl_summary(ubl_xml: str) -> Dict[str, Any]:
    """Best-effort extract of number/date/currency/total and supplier Peppol id."""
    out: Dict[str, Any] = {
        "document_type": None,
        "document_number": None,
        "issue_date": None,
        "currency": None,
        "total_amount": None,
        "supplier_scheme_id": None,
        "supplier_endpoint_id": None,
        "supplier_peppol_id": None,
    }
    if not ubl_xml or not ubl_xml.strip():
        return out
    try:
        root = ET.fromstring(ubl_xml)
    except ET.ParseError:
        return out

    local = _local_tag(root.tag).lower()
    if "creditnote" in local:
        out["document_type"] = "credit_note"
    elif "invoice" in local:
        out["document_type"] = "invoice"
    else:
        out["document_type"] = local or None

    def find_text(*paths: str) -> Optional[str]:
        for path in paths:
            el = root.find(path, _UBL_NS)
            if el is not None and el.text and el.text.strip():
                return el.text.strip()
        return None

    out["document_number"] = find_text("cbc:ID")
    out["issue_date"] = _parse_date(find_text("cbc:IssueDate"))
    out["currency"] = find_text("cbc:DocumentCurrencyCode")
    out["total_amount"] = _parse_amount(
        find_text(
            "cac:LegalMonetaryTotal/cbc:PayableAmount",
            "cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount",
        )
    )

    endpoint = root.find(
        "cac:AccountingSupplierParty/cac:Party/cbc:EndpointID",
        _UBL_NS,
    )
    if endpoint is not None and endpoint.text and endpoint.text.strip():
        scheme = (endpoint.attrib.get("schemeID") or "").strip() or None
        value = endpoint.text.strip()
        out["supplier_scheme_id"] = scheme
        out["supplier_endpoint_id"] = value
        if scheme and not value.startswith(f"{scheme}:"):
            out["supplier_peppol_id"] = f"{scheme}:{value}"
        else:
            out["supplier_peppol_id"] = value
    return out


def match_client_by_peppol_id(peppol_id: Optional[str]) -> Optional[Client]:
    """Match a Client whose custom_fields store the supplier Peppol endpoint."""
    if not peppol_id:
        return None
    raw = peppol_id.strip()
    if not raw:
        return None
    scheme = None
    endpoint = raw
    if ":" in raw:
        scheme, endpoint = raw.split(":", 1)
        scheme = scheme.strip() or None
        endpoint = endpoint.strip()

    # Prefer exact JSON contains when the DB dialect supports it; fall back to Python scan.
    clients = Client.query.order_by(Client.id.asc()).limit(5000).all()
    for client in clients:
        fields = client.custom_fields or {}
        if not isinstance(fields, dict):
            continue
        cf_endpoint = str(fields.get("peppol_endpoint_id") or "").strip()
        cf_scheme = str(fields.get("peppol_scheme_id") or "").strip() or None
        if not cf_endpoint:
            continue
        if cf_endpoint == raw or cf_endpoint == endpoint:
            if not scheme or not cf_scheme or cf_scheme == scheme:
                return client
        combined = f"{cf_scheme}:{cf_endpoint}" if cf_scheme else cf_endpoint
        if combined == raw:
            return client
    return None


class PeppolInboundService:
    """Import inbound Peppol documents from the local peppol-bridge inbox API."""

    def __init__(self, *, timeout_s: Optional[float] = None):
        self.settings = Settings.get_settings()
        if timeout_s is not None:
            self.timeout_s = float(timeout_s)
        else:
            try:
                self.timeout_s = float(getattr(self.settings, "peppol_access_point_timeout", None) or 30)
            except (TypeError, ValueError):
                self.timeout_s = 30.0

    def inbox_enabled(self) -> bool:
        from app.integrations.peppol import peppol_enabled

        if not peppol_enabled():
            return False
        return _bool_setting(self.settings, "peppol_inbox_enabled", default=False)

    def _auth_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        token = ""
        try:
            token = self.settings.get_secret("peppol_access_point_token") or ""
        except Exception:
            token = getattr(self.settings, "peppol_access_point_token", "") or ""
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _inbox_urls(self) -> Tuple[Optional[str], Optional[str]]:
        base = bridge_base_url_from_access_point(getattr(self.settings, "peppol_access_point_url", "") or "")
        if not base:
            return None, None
        return f"{base}/inbox", f"{base}/inbox/ack"

    def fetch_inbox(self, *, size: int = 100) -> List[Dict[str, Any]]:
        inbox_url, _ = self._inbox_urls()
        if not inbox_url:
            raise RuntimeError("Peppol access point URL is not configured")
        resp = requests.get(
            inbox_url,
            headers=self._auth_headers(),
            params={"size": max(1, min(int(size or 100), 500))},
            timeout=self.timeout_s,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Bridge inbox HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        if not isinstance(data, dict) or not data.get("ok"):
            raise RuntimeError(f"Bridge inbox error: {data}")
        docs = data.get("documents") or []
        if not isinstance(docs, list):
            raise RuntimeError("Bridge inbox returned unexpected documents payload")
        return [d for d in docs if isinstance(d, dict)]

    def ack_downloaded(self, external_ids: List[str]) -> None:
        _, ack_url = self._inbox_urls()
        if not ack_url:
            raise RuntimeError("Peppol access point URL is not configured")
        ids = [str(i).strip() for i in external_ids if str(i).strip()]
        if not ids:
            return
        resp = requests.post(
            ack_url,
            headers={**self._auth_headers(), "Content-Type": "application/json"},
            json={"ids": ids},
            timeout=self.timeout_s,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Bridge inbox ack HTTP {resp.status_code}: {resp.text[:300]}")

    def upsert_document(
        self, payload: Dict[str, Any], *, provider: str = "letspeppol"
    ) -> Tuple[PeppolInboundDocument, bool]:
        """Create or update a local inbound row. Returns (row, created)."""
        external_id = str(payload.get("id") or "").strip()
        if not external_id:
            raise ValueError("Inbound document missing id")

        ubl_xml = payload.get("ubl")
        if ubl_xml is not None and not isinstance(ubl_xml, str):
            ubl_xml = str(ubl_xml)
        ubl_xml = ubl_xml or None

        summary = parse_ubl_summary(ubl_xml or "")
        doc_type = payload.get("type")
        if isinstance(doc_type, str) and doc_type.strip():
            mapped = doc_type.strip().lower()
            if mapped == "credit_note" or mapped == "creditnote":
                summary["document_type"] = "credit_note"
            elif mapped == "invoice":
                summary["document_type"] = "invoice"
            else:
                summary["document_type"] = mapped

        partner = (payload.get("partnerPeppolId") or summary.get("supplier_peppol_id") or "").strip() or None
        owner = (payload.get("ownerPeppolId") or "").strip() or None
        matched = match_client_by_peppol_id(partner)

        existing = PeppolInboundDocument.query.filter_by(external_id=external_id).first()
        created = existing is None
        row = existing or PeppolInboundDocument(external_id=external_id, provider=provider or "letspeppol")
        row.provider = provider or row.provider or "letspeppol"
        row.direction = "inbound"
        row.partner_peppol_id = partner
        row.owner_peppol_id = owner
        row.document_type = summary.get("document_type")
        row.document_number = summary.get("document_number")
        row.issue_date = summary.get("issue_date")
        row.currency = summary.get("currency")
        row.total_amount = summary.get("total_amount")
        if ubl_xml:
            row.ubl_xml = ubl_xml
            row.ubl_sha256 = _sha256(ubl_xml)
        row.processed_status = (
            (payload.get("processedStatus") or None) if payload.get("processedStatus") else row.processed_status
        )
        # Keep a trimmed copy of transport metadata (not the full UBL again).
        row.raw_payload = {
            k: payload.get(k)
            for k in (
                "id",
                "direction",
                "type",
                "ownerPeppolId",
                "partnerPeppolId",
                "createdOn",
                "scheduledOn",
                "processedOn",
                "processedStatus",
            )
            if k in payload
        }
        if matched is not None:
            row.matched_client_id = matched.id
        if created:
            row.status = "new"
            db.session.add(row)
        return row, created

    def poll_and_import(self, *, size: int = 100) -> Dict[str, Any]:
        """Fetch inbox, upsert locally, ack successfully stored ids."""
        if not self.inbox_enabled():
            return {"ok": True, "skipped": True, "reason": "inbox_disabled"}

        try:
            documents = self.fetch_inbox(size=size)
        except Exception as e:
            logger.warning("Peppol inbox fetch failed: %s", e)
            return {"ok": False, "error": str(e)}

        created_count = 0
        updated_count = 0
        ack_ids: List[str] = []
        errors: List[str] = []

        provider_label = (getattr(self.settings, "peppol_provider", None) or "letspeppol").strip() or "letspeppol"

        for payload in documents:
            external_id = str(payload.get("id") or "").strip()
            try:
                row, created = self.upsert_document(payload, provider=provider_label)
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                if external_id:
                    ack_ids.append(external_id)
                # Persist per document so a later failure does not lose earlier imports.
                if not safe_commit("peppol_inbound_upsert"):
                    raise RuntimeError("Database commit failed while importing inbound Peppol document")
                if row.status == "error":
                    row.status = "new"
                    row.error_message = None
            except Exception as e:
                logger.exception("Failed to import inbound Peppol document %s", external_id or "?")
                errors.append(f"{external_id or '?'}: {e}")
                db.session.rollback()

        acked = 0
        if ack_ids:
            try:
                self.ack_downloaded(ack_ids)
                acked = len(ack_ids)
                for ext_id in ack_ids:
                    row = PeppolInboundDocument.query.filter_by(external_id=ext_id).first()
                    if row and row.status != "error":
                        row.mark_acknowledged()
                safe_commit("peppol_inbound_ack")
            except Exception as e:
                logger.warning("Peppol inbox ack failed after import: %s", e)
                errors.append(f"ack: {e}")

        return {
            "ok": len(errors) == 0,
            "fetched": len(documents),
            "created": created_count,
            "updated": updated_count,
            "acked": acked,
            "errors": errors,
        }
