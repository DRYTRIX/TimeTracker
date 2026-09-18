"""ADP Workforce Now payroll connector."""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict
from urllib.parse import urlencode

import requests

from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)


class AdpConnector(BaseConnector):
    """ADP Workforce Now — OAuth2 client credentials / auth code + payroll batches."""

    display_name = "ADP Workforce Now"
    description = "Push payroll batches to ADP Workforce Now"
    icon = "adp"

    AUTH_URL = "https://accounts.adp.com/auth/oauth/v2/authorize"
    TOKEN_URL = "https://accounts.adp.com/auth/oauth/v2/token"
    API_BASE = "https://api.adp.com"

    @property
    def provider_name(self) -> str:
        return "adp"

    def _creds(self):
        from app.models import Settings

        settings = Settings.get_settings()
        c = settings.get_integration_credentials("adp")
        return {
            "client_id": c.get("client_id") or os.getenv("ADP_CLIENT_ID"),
            "client_secret": c.get("client_secret") or os.getenv("ADP_CLIENT_SECRET"),
        }

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        c = self._creds()
        if not c["client_id"]:
            raise ValueError("ADP_CLIENT_ID not configured")
        params = {
            "client_id": c["client_id"],
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "openid",
            "state": state or "",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        c = self._creds()
        r = requests.post(
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
        r.raise_for_status()
        data = r.json()
        expires_at = datetime.utcnow() + timedelta(seconds=int(data.get("expires_in", 3600)))
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at.isoformat(),
            "token_type": data.get("token_type", "Bearer"),
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        c = self._creds()
        # Prefer refresh_token; fall back to client_credentials for server apps
        if self.credentials and self.credentials.refresh_token:
            data_body = {
                "grant_type": "refresh_token",
                "refresh_token": self.credentials.refresh_token,
                "client_id": c["client_id"],
                "client_secret": c["client_secret"],
            }
        else:
            data_body = {
                "grant_type": "client_credentials",
                "client_id": c["client_id"],
                "client_secret": c["client_secret"],
            }
        r = requests.post(self.TOKEN_URL, data=data_body, timeout=30)
        r.raise_for_status()
        data = r.json()
        expires_at = datetime.utcnow() + timedelta(seconds=int(data.get("expires_in", 3600)))
        if self.credentials:
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
        r = requests.get(
            f"{self.API_BASE}/hr/v2/workers",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params={"$top": 1},
            timeout=20,
        )
        if r.status_code in (200, 401, 403):
            # 401/403 still prove reachability; partnership scopes vary
            if r.status_code == 200:
                return {"success": True, "message": "ADP connection OK"}
            return {"success": True, "message": f"ADP reachable (HTTP {r.status_code} — check scopes)"}
        return {"success": False, "message": f"HTTP {r.status_code}: {r.text[:200]}"}

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        from app.services.payroll_sync_service import PayrollSyncService

        return PayrollSyncService().push_period(
            provider="adp",
            integration=self.integration,
            connector=self,
        )

    def push_payroll_batch(self, batch: Dict[str, Any]) -> Dict[str, Any]:
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "Missing access token"}
        payload = {
            "events": [
                {
                    "data": {
                        "eventContext": {
                            "payrollGroupCode": (self.integration.config or {}).get("payroll_group_code", "DEFAULT"),
                        },
                        "transform": {
                            "payDataInput": {
                                "payrollPeriodStartDate": batch["period_start"],
                                "payrollPeriodEndDate": batch["period_end"],
                                "workers": batch.get("employees", []),
                            }
                        },
                    }
                }
            ]
        }
        r = requests.post(
            f"{self.API_BASE}/events/payroll/v1/pay-data-input.modify",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if r.status_code in (200, 201, 202):
            data = r.json() if r.content else {}
            return {
                "success": True,
                "external_batch_id": str(data.get("events", [{}])[0].get("eventID") or ""),
                "raw": data,
            }
        return {"success": False, "message": f"HTTP {r.status_code}: {r.text[:300]}"}
