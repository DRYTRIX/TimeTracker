"""Outlook / Microsoft Graph email sync for CRM."""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List
from urllib.parse import urlencode

import requests

from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)


class OutlookEmailConnector(BaseConnector):
    """Microsoft Graph mail connector."""

    display_name = "Outlook Email"
    description = "Sync Outlook / Microsoft 365 mail into CRM"
    icon = "outlook"

    AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    API_BASE = "https://graph.microsoft.com/v1.0"

    @property
    def provider_name(self) -> str:
        return "outlook_email"

    def _creds(self):
        from app.models import Settings

        settings = Settings.get_settings()
        c = settings.get_integration_credentials("outlook_email")
        # Reuse Teams / Outlook Calendar app registration when dedicated creds missing
        fallback = settings.get_integration_credentials("microsoft_teams") or {}
        return {
            "client_id": c.get("client_id")
            or os.getenv("OUTLOOK_EMAIL_CLIENT_ID")
            or os.getenv("MICROSOFT_CLIENT_ID")
            or fallback.get("client_id"),
            "client_secret": c.get("client_secret")
            or os.getenv("OUTLOOK_EMAIL_CLIENT_SECRET")
            or os.getenv("MICROSOFT_CLIENT_SECRET")
            or fallback.get("client_secret"),
        }

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        c = self._creds()
        if not c["client_id"]:
            raise ValueError("OUTLOOK_EMAIL_CLIENT_ID / MICROSOFT_CLIENT_ID not configured")
        params = {
            "client_id": c["client_id"],
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": " ".join(
                [
                    "offline_access",
                    "User.Read",
                    "Mail.Read",
                ]
            ),
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
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
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
            "scope": data.get("scope"),
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
        expires_at = datetime.utcnow() + timedelta(seconds=int(data.get("expires_in", 3600)))
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
            f"{self.API_BASE}/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        if r.status_code == 200:
            return {"success": True, "message": f"Outlook OK ({r.json().get('mail') or r.json().get('userPrincipalName')})"}
        return {"success": False, "message": f"HTTP {r.status_code}"}

    def list_recent_threads(self, max_results: int = 25) -> List[Dict[str, Any]]:
        token = self.get_access_token()
        if not token:
            return []
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(
            f"{self.API_BASE}/me/messages",
            headers=headers,
            params={
                "$top": max_results,
                "$orderby": "receivedDateTime desc",
                "$select": "id,conversationId,subject,bodyPreview,from,toRecipients,receivedDateTime,body",
            },
            timeout=30,
        )
        r.raise_for_status()
        by_conv: Dict[str, Dict[str, Any]] = {}
        for msg in r.json().get("value", []):
            conv = msg.get("conversationId") or msg.get("id")
            frm = (msg.get("from") or {}).get("emailAddress", {}).get("address", "")
            to_list = [
                t.get("emailAddress", {}).get("address", "")
                for t in (msg.get("toRecipients") or [])
                if t.get("emailAddress")
            ]
            sent_at = None
            if msg.get("receivedDateTime"):
                try:
                    sent_at = datetime.fromisoformat(msg["receivedDateTime"].replace("Z", "+00:00"))
                except Exception:
                    pass
            entry = {
                "id": msg.get("id"),
                "from": frm,
                "to": to_list,
                "subject": msg.get("subject"),
                "snippet": msg.get("bodyPreview"),
                "body_text": (msg.get("body") or {}).get("content") if (msg.get("body") or {}).get("contentType") == "text" else None,
                "sent_at": sent_at,
            }
            if conv not in by_conv:
                by_conv[conv] = {
                    "id": conv,
                    "subject": msg.get("subject"),
                    "snippet": msg.get("bodyPreview"),
                    "participants": set(),
                    "messages": [],
                }
            by_conv[conv]["participants"].add(frm)
            for a in to_list:
                by_conv[conv]["participants"].add(a)
            by_conv[conv]["messages"].append(entry)

        result = []
        for t in by_conv.values():
            t["participants"] = list(t["participants"])
            result.append(t)
        return result

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        from app.services.email_sync_service import EmailSyncService

        threads = self.list_recent_threads()
        result = EmailSyncService().ingest_threads("outlook", threads)
        return {"success": True, "synced": result.get("created", 0) + result.get("updated", 0), **result}
