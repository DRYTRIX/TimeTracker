"""Sage Business Cloud accounting connector."""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)


class SageConnector(BaseConnector):
    """Sage Business Cloud Accounting (OAuth2 + REST)."""

    display_name = "Sage Business Cloud"
    description = "Sync invoices, contacts, and payments with Sage"
    icon = "sage"

    AUTH_URL = "https://www.sageone.com/oauth2/auth/central"
    TOKEN_URL = "https://oauth.accounting.sage.com/token"
    API_BASE = "https://api.accounting.sage.com/v3.1"

    @property
    def provider_name(self) -> str:
        return "sage"

    def _creds(self):
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("sage")
        return {
            "client_id": creds.get("client_id") or os.getenv("SAGE_CLIENT_ID"),
            "client_secret": creds.get("client_secret") or os.getenv("SAGE_CLIENT_SECRET"),
        }

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        c = self._creds()
        if not c["client_id"]:
            raise ValueError("SAGE_CLIENT_ID not configured")
        params = {
            "response_type": "code",
            "client_id": c["client_id"],
            "redirect_uri": redirect_uri,
            "scope": "full_access",
            "state": state or "",
            "filter": "apiv3.1",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        c = self._creds()
        if not c["client_id"] or not c["client_secret"]:
            raise ValueError("Sage OAuth credentials not configured")
        response = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": c["client_id"],
                "client_secret": c["client_secret"],
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        expires_at = None
        if data.get("expires_in"):
            expires_at = datetime.utcnow() + timedelta(seconds=int(data["expires_in"]))
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "token_type": data.get("token_type", "Bearer"),
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        if not self.credentials or not self.credentials.refresh_token:
            raise ValueError("No refresh token available")
        c = self._creds()
        response = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.credentials.refresh_token,
                "client_id": c["client_id"],
                "client_secret": c["client_secret"],
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        expires_at = None
        if data.get("expires_in"):
            expires_at = datetime.utcnow() + timedelta(seconds=int(data["expires_in"]))
        self.credentials.access_token = data.get("access_token")
        if data.get("refresh_token"):
            self.credentials.refresh_token = data["refresh_token"]
        self.credentials.expires_at = expires_at
        from app import db

        db.session.commit()
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

    def test_connection(self) -> Dict[str, Any]:
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token"}
        try:
            r = requests.get(
                f"{self.API_BASE}/businesses",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                timeout=20,
            )
            if r.status_code == 200:
                return {"success": True, "message": "Connected to Sage Business Cloud"}
            return {"success": False, "message": f"HTTP {r.status_code}: {r.text[:200]}"}
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Push open invoices to Sage as sales invoices."""
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "Not authenticated", "synced": 0}

        from app.models import Invoice

        invoices = Invoice.query.filter(Invoice.status.in_(["sent", "paid", "draft"])).limit(50).all()
        synced = 0
        errors = []
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}

        for inv in invoices:
            try:
                payload = {
                    "sales_invoice": {
                        "reference": inv.invoice_number,
                        "date": (inv.issue_date or datetime.utcnow().date()).isoformat(),
                        "due_date": inv.due_date.isoformat() if inv.due_date else None,
                        "contact_name": inv.client_name,
                        "notes": inv.notes or "",
                        "invoice_lines": [
                            {
                                "description": item.description or "Service",
                                "quantity": float(item.quantity or 1),
                                "unit_price": float(item.unit_price or 0),
                            }
                            for item in (inv.items or [])
                        ]
                        or [{"description": "Invoice total", "quantity": 1, "unit_price": float(inv.total_amount or 0)}],
                    }
                }
                r = requests.post(f"{self.API_BASE}/sales_invoices", headers=headers, json=payload, timeout=30)
                if r.status_code in (200, 201):
                    synced += 1
                else:
                    errors.append(f"{inv.invoice_number}: {r.status_code}")
            except Exception as exc:
                errors.append(f"{inv.invoice_number}: {exc}")
                logger.exception("Sage sync failed for invoice %s", inv.id)

        return {"success": len(errors) == 0, "synced": synced, "errors": errors, "message": f"Synced {synced} invoices"}
