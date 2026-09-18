"""DATEV accounting connector (file-based EXTF / Buchungsstapel export)."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from app.integrations.base import BaseConnector
from app.utils.datev_export import build_datev_buchungsstapel

logger = logging.getLogger(__name__)


class DatevConnector(BaseConnector):
    """DATEV export connector — generates EXTF CSV for Buchungsstapel import."""

    display_name = "DATEV"
    description = "Export invoices as DATEV EXTF Buchungsstapel CSV"
    icon = "datev"

    @property
    def provider_name(self) -> str:
        return "datev"

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        # File-based — no OAuth; return a stub that integrations UI can skip
        return redirect_uri or "/"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        return {
            "access_token": "datev-file-export",
            "refresh_token": None,
            "expires_at": None,
            "token_type": "none",
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        return {"access_token": "datev-file-export", "expires_at": None}

    def test_connection(self) -> Dict[str, Any]:
        config = (self.integration.config if self.integration else {}) or {}
        consultant = config.get("consultant_number") or config.get("berater_nr")
        client_nr = config.get("client_number") or config.get("mandant_nr")
        if not consultant or not client_nr:
            return {
                "success": False,
                "message": "Configure consultant number (Berater-Nr) and client number (Mandanten-Nr)",
            }
        return {"success": True, "message": f"DATEV ready (Berater {consultant}, Mandant {client_nr})"}

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Generate DATEV export content and store path/summary on the integration."""
        from app.models import Invoice

        config = (self.integration.config if self.integration else {}) or {}
        invoices: List = Invoice.query.filter(Invoice.status.in_(["sent", "paid"])).limit(500).all()
        csv_content = build_datev_buchungsstapel(
            invoices,
            consultant_number=str(config.get("consultant_number") or config.get("berater_nr") or "00000"),
            client_number=str(config.get("client_number") or config.get("mandant_nr") or "00000"),
            account_revenue=str(config.get("account_revenue") or "8400"),
            account_receivable=str(config.get("account_receivable") or "10000"),
        )
        filename = f"EXTF_Buchungsstapel_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        # Persist last export in config for download via integrations UI
        if self.integration:
            cfg = dict(self.integration.config or {})
            cfg["last_export_filename"] = filename
            cfg["last_export_at"] = datetime.utcnow().isoformat()
            cfg["last_export_preview"] = csv_content[:2000]
            cfg["last_export_content"] = csv_content
            self.integration.config = cfg
            from app import db

            db.session.commit()

        return {
            "success": True,
            "synced": len(invoices),
            "filename": filename,
            "message": f"Generated DATEV export with {len(invoices)} invoices",
            "content": csv_content,
        }
