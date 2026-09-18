"""Gmail integration for CRM email sync."""

import logging
import os
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)


class GmailConnector(BaseConnector):
    """Gmail API connector — syncs threads matched to CRM contacts."""

    display_name = "Gmail"
    description = "Sync Gmail threads into CRM (clients, leads, deals)"
    icon = "gmail"

    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_BASE = "https://gmail.googleapis.com/gmail/v1"

    @property
    def provider_name(self) -> str:
        return "gmail"

    def _creds(self):
        from app.models import Settings

        settings = Settings.get_settings()
        c = settings.get_integration_credentials("gmail")
        return {
            "client_id": c.get("client_id") or os.getenv("GMAIL_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": c.get("client_secret")
            or os.getenv("GMAIL_CLIENT_SECRET")
            or os.getenv("GOOGLE_CLIENT_SECRET"),
        }

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        c = self._creds()
        if not c["client_id"]:
            raise ValueError("GMAIL_CLIENT_ID / GOOGLE_CLIENT_ID not configured")
        params = {
            "client_id": c["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(
                [
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/userinfo.email",
                ]
            ),
            "access_type": "offline",
            "prompt": "consent",
            "state": state or "",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        c = self._creds()
        r = requests.post(
            self.TOKEN_URL,
            data={
                "code": code,
                "client_id": c["client_id"],
                "client_secret": c["client_secret"],
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
        self.credentials.expires_at = expires_at
        from app import db

        db.session.commit()
        return {"access_token": data["access_token"], "expires_at": expires_at.isoformat()}

    def test_connection(self) -> Dict[str, Any]:
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "Not authenticated"}
        r = requests.get(
            f"{self.API_BASE}/users/me/profile",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        if r.status_code == 200:
            return {"success": True, "message": f"Gmail OK ({r.json().get('emailAddress', '')})"}
        return {"success": False, "message": f"HTTP {r.status_code}"}

    def list_recent_threads(self, max_results: int = 25) -> List[Dict[str, Any]]:
        token = self.get_access_token()
        if not token:
            return []
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(
            f"{self.API_BASE}/users/me/threads",
            headers=headers,
            params={"maxResults": max_results},
            timeout=30,
        )
        r.raise_for_status()
        threads = []
        for item in r.json().get("threads", []):
            detail = requests.get(
                f"{self.API_BASE}/users/me/threads/{item['id']}",
                headers=headers,
                params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Date"]},
                timeout=30,
            )
            if detail.status_code != 200:
                continue
            data = detail.json()
            messages_out = []
            participants = set()
            subject = ""
            for msg in data.get("messages", []):
                headers_map = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
                subject = headers_map.get("subject") or subject
                frm = headers_map.get("from", "")
                to = headers_map.get("to", "")
                participants.add(frm)
                for addr in to.split(","):
                    if addr.strip():
                        participants.add(addr.strip())
                sent_at = None
                try:
                    if headers_map.get("date"):
                        sent_at = parsedate_to_datetime(headers_map["date"])
                except Exception:
                    pass
                messages_out.append(
                    {
                        "id": msg.get("id"),
                        "from": frm,
                        "to": [a.strip() for a in to.split(",") if a.strip()],
                        "subject": headers_map.get("subject"),
                        "snippet": msg.get("snippet"),
                        "sent_at": sent_at,
                    }
                )
            threads.append(
                {
                    "id": item["id"],
                    "subject": subject,
                    "snippet": data.get("messages", [{}])[-1].get("snippet") if data.get("messages") else "",
                    "participants": list(participants),
                    "messages": messages_out,
                }
            )
        return threads

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        from app.services.email_sync_service import EmailSyncService

        threads = self.list_recent_threads()
        result = EmailSyncService().ingest_threads("gmail", threads)
        return {"success": True, "synced": result.get("created", 0) + result.get("updated", 0), **result}
