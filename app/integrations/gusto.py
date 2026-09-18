"""Gusto payroll connector."""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict
from urllib.parse import urlencode

import requests

from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)


class GustoConnector(BaseConnector):
    """Gusto Partner API — push payroll hours / pay runs."""

    display_name = "Gusto"
    description = "Push time entries as payroll hours to Gusto"
    icon = "gusto"

    AUTH_URL = "https://api.gusto.com/oauth/authorize"
    TOKEN_URL = "https://api.gusto.com/oauth/token"
    API_BASE = "https://api.gusto.com/v1"

    @property
    def provider_name(self) -> str:
        return "gusto"

    def _creds(self):
        from app.models import Settings

        settings = Settings.get_settings()
        c = settings.get_integration_credentials("gusto")
        return {
            "client_id": c.get("client_id") or os.getenv("GUSTO_CLIENT_ID"),
            "client_secret": c.get("client_secret") or os.getenv("GUSTO_CLIENT_SECRET"),
        }

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        c = self._creds()
        if not c["client_id"]:
            raise ValueError("GUSTO_CLIENT_ID not configured")
        params = {
            "client_id": c["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state or "",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        c = self._creds()
        r = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": c["client_id"],
                "client_secret": c["client_secret"],
                "redirect_uri": redirect_uri,
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        expires_at = datetime.utcnow() + timedelta(seconds=int(data.get("expires_in", 7200)))
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at.isoformat(),
            "token_type": data.get("token_type", "Bearer"),
            "extra_data": {"company_uuid": data.get("company_uuid") or (self.integration.config or {}).get("company_uuid")},
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        if not self.credentials or not self.credentials.refresh_token:
            raise ValueError("No refresh token")
        c = self._creds()
        r = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": c["client_id"],
                "client_secret": c["client_secret"],
                "refresh_token": self.credentials.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        expires_at = datetime.utcnow() + timedelta(seconds=int(data.get("expires_in", 7200)))
        self.credentials.access_token = data["access_token"]
        if data.get("refresh_token"):
            self.credentials.refresh_token = data["refresh_token"]
        self.credentials.expires_at = expires_at
        from app import db

        db.session.commit()
        return {"access_token": data["access_token"], "expires_at": expires_at.isoformat()}

    def test_connection(self) -> Dict[str, Any]:
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "Not authenticated"}
        company = (self.integration.config or {}).get("company_uuid")
        if not company:
            return {"success": False, "message": "Set company_uuid in integration config"}
        r = requests.get(
            f"{self.API_BASE}/companies/{company}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=20,
        )
        if r.status_code == 200:
            return {"success": True, "message": f"Gusto company: {r.json().get('name', company)}"}
        return {"success": False, "message": f"HTTP {r.status_code}: {r.text[:200]}"}

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        from app.services.payroll_sync_service import PayrollSyncService

        return PayrollSyncService().push_period(
            provider="gusto",
            integration=self.integration,
            connector=self,
        )

    def push_payroll_batch(self, batch: Dict[str, Any]) -> Dict[str, Any]:
        token = self.get_access_token()
        company = (self.integration.config or {}).get("company_uuid")
        if not token or not company:
            return {"success": False, "message": "Missing token or company_uuid"}
        # Gusto payrolls API varies by partnership; post a summary payload for partner sandbox
        r = requests.post(
            f"{self.API_BASE}/companies/{company}/payrolls",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "start_date": batch["period_start"],
                "end_date": batch["period_end"],
                "employee_compensations": batch.get("employees", []),
            },
            timeout=60,
        )
        if r.status_code in (200, 201):
            data = r.json() if r.content else {}
            return {"success": True, "external_batch_id": str(data.get("uuid") or data.get("id") or ""), "raw": data}
        return {"success": False, "message": f"HTTP {r.status_code}: {r.text[:300]}"}
