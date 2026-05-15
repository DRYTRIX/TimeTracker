"""
GitHub connector — webhook-driven Task automation + manual issue sync.

This is a deliberately small, opt-in connector that sits alongside the
fully-featured OAuth-based :class:`app.integrations.github.GitHubConnector`.
It uses a personal-access token instead of OAuth and stores everything
(token, repo info, webhook secret, feature flags) inside
``Integration.config`` so no extra tables are required.

The connector is per-user (Integration.user_id is set, is_global=False)
and uses the provider key ``"github_connector"`` so it never collides with
the existing global ``"github"`` integration.

All public methods return JSON-serialisable ``dict`` results and degrade
gracefully when the integration row is missing or ``is_active`` is False.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from app.integrations.base import BaseConnector
from app.utils.secret_crypto import decrypt_if_needed, encrypt_if_possible
from app.utils.secret_crypto import is_configured as secrets_encryption_configured

logger = logging.getLogger(__name__)

PROVIDER_KEY = "github_connector"
HTTP_TIMEOUT = 10
GITHUB_API = "https://api.github.com"

# GitHub label → TimeTracker priority. Anything else falls back to "low".
_LABEL_PRIORITY = {
    "bug": "high",
    "critical": "high",
    "enhancement": "medium",
}


def _mask(token: Optional[str]) -> str:
    """Return a log-safe representation of a token (only prefix + ellipsis)."""
    if not token:
        return "(empty)"
    return f"{token[:4]}..."


def _enc(value: Optional[str]) -> Optional[str]:
    """Encrypt a secret if possible; fall through to plain text on missing key."""
    if value is None:
        return None
    value = (value or "").strip()
    if not value:
        return ""
    if secrets_encryption_configured():
        try:
            return encrypt_if_possible(value)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("GitHub secret encryption failed; storing plaintext: %s", exc)
    return value


def _dec(value: Optional[str]) -> str:
    """Decrypt a previously-encrypted secret; pass through plain text safely."""
    if not value:
        return ""
    try:
        return decrypt_if_needed(value)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("GitHub secret decryption failed: %s", exc)
        return ""


class GitHubConnector(BaseConnector):
    """Webhook-driven GitHub integration (per-user, PAT-based)."""

    display_name = "GitHub"
    description = "Auto-create tasks from GitHub issues and run a timer on assignment"
    icon = "github"

    def __init__(self, integration=None, credentials=None):
        """Accept the standard ``(integration, credentials)`` signature but
        credentials are optional — this connector stores its token in
        ``integration.config``."""
        super().__init__(integration, credentials)

    # ------------------------------------------------------------------
    # BaseConnector abstract surface — most are no-ops for the PAT flow.
    # ------------------------------------------------------------------
    @property
    def provider_name(self) -> str:
        return PROVIDER_KEY

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        raise NotImplementedError("GitHubConnector uses a personal access token, not OAuth.")

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        raise NotImplementedError("GitHubConnector uses a personal access token, not OAuth.")

    def refresh_access_token(self) -> Dict[str, Any]:
        return {"access_token": self._token() or None}

    # ------------------------------------------------------------------
    # Config / secret helpers
    # ------------------------------------------------------------------
    def _cfg(self) -> Dict[str, Any]:
        return dict(self.integration.config or {}) if self.integration else {}

    def _token(self) -> str:
        return _dec(self._cfg().get("github_token"))

    def _webhook_secret(self) -> str:
        return _dec(self._cfg().get("webhook_secret"))

    def _is_ready(self) -> bool:
        return bool(self.integration and self.integration.is_active and self._token())

    @classmethod
    def save_config(cls, integration, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Persist UI config to ``integration.config`` (token/webhook secret encrypted)."""
        from app import db
        from app.utils.db import safe_commit

        if not integration:
            return {"ok": False, "error": "Integration not configured"}

        merged: Dict[str, Any] = dict(integration.config or {})

        token = (new_config.get("github_token") or "").strip()
        if token:
            merged["github_token"] = _enc(token)
        secret = (new_config.get("webhook_secret") or "").strip()
        if secret:
            merged["webhook_secret"] = _enc(secret)

        for key in ("repo_owner", "repo_name", "label_filter"):
            if key in new_config:
                merged[key] = (new_config.get(key) or "").strip() or None

        if "default_project_id" in new_config:
            try:
                merged["default_project_id"] = int(new_config["default_project_id"])
            except (TypeError, ValueError):
                merged["default_project_id"] = None

        if "auto_start_timer" in new_config:
            merged["auto_start_timer"] = bool(new_config["auto_start_timer"])

        integration.config = merged
        integration.is_active = bool(merged.get("github_token"))
        integration.updated_at = datetime.utcnow()

        if not safe_commit("github_connector_save_config", {"integration_id": integration.id}):
            return {"ok": False, "error": "Database error while saving configuration"}
        return {"ok": True, "is_active": bool(integration.is_active)}

    # ------------------------------------------------------------------
    # Connection test
    # ------------------------------------------------------------------
    def test_connection(self) -> Dict[str, Any]:
        if not self._is_ready():
            return {"success": False, "message": "Integration not configured"}
        token = self._token()
        logger.debug("GitHubConnector.test_connection using token=%s", _mask(token))
        try:
            resp = requests.get(
                f"{GITHUB_API}/user",
                headers=self._headers(),
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            logger.warning("GitHub test_connection request failed: %s", exc)
            return {"success": False, "message": f"Connection error: {exc}"}

        if resp.status_code == 200:
            return {"success": True, "message": f"Connected as {resp.json().get('login', 'Unknown')}"}
        return {"success": False, "message": f"GitHub returned HTTP {resp.status_code}"}

    # ------------------------------------------------------------------
    # Manual sync — POST /api/integrations/github/sync
    # ------------------------------------------------------------------
    def sync(self) -> Dict[str, Any]:
        if not self._is_ready():
            return {"ok": False, "error": "Integration not configured"}

        cfg = self._cfg()
        owner = cfg.get("repo_owner")
        repo = cfg.get("repo_name")
        project_id = cfg.get("default_project_id")
        label_filter = (cfg.get("label_filter") or "").strip().lower() or None

        if not owner or not repo:
            return {"ok": False, "error": "repo_owner and repo_name are required"}
        if not project_id:
            return {"ok": False, "error": "default_project_id is required"}

        try:
            resp = requests.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/issues",
                headers=self._headers(),
                params={"state": "open", "per_page": 50},
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            logger.warning("GitHub sync request failed for %s/%s: %s", owner, repo, exc)
            return {"ok": False, "error": f"GitHub request failed: {exc}"}

        if resp.status_code != 200:
            return {"ok": False, "error": f"GitHub returned HTTP {resp.status_code}"}

        issues = resp.json() or []
        synced = 0
        skipped = 0
        errors: List[str] = []

        from app import db
        from app.models import Task
        from app.utils.db import safe_commit

        for issue in issues:
            if issue.get("pull_request"):
                skipped += 1
                continue
            number = issue.get("number")
            if not number:
                skipped += 1
                continue

            labels = [(lbl.get("name") or "").lower() for lbl in (issue.get("labels") or [])]
            if label_filter and label_filter not in labels:
                skipped += 1
                continue

            external_ref = f"github_issue_{number}"
            existing = Task.query.filter_by(project_id=int(project_id), external_ref=external_ref).first()
            if existing:
                skipped += 1
                continue

            try:
                task = self._build_task_from_issue(issue, int(project_id), external_ref)
                db.session.add(task)
                synced += 1
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to create task for issue #%s: %s", number, exc)
                errors.append(f"#{number}: {exc}")

        if synced:
            if not safe_commit("github_connector_sync", {"integration_id": self.integration.id}):
                return {
                    "ok": False,
                    "error": "Database error while saving synced issues",
                    "synced": 0,
                    "skipped": skipped,
                    "errors": errors,
                }

        try:
            self.integration.last_sync_at = datetime.utcnow()
            self.integration.last_sync_status = "success" if not errors else "partial"
            safe_commit("github_connector_sync_status", {"integration_id": self.integration.id})
        except Exception:
            pass

        return {"ok": True, "synced": synced, "skipped": skipped, "errors": errors}

    # ------------------------------------------------------------------
    # Webhook handler — POST /api/integrations/github/webhook
    # ------------------------------------------------------------------
    def handle_webhook(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        raw_body: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """Process a webhook delivery from GitHub.

        Returns a dict shaped like ``{"status": int, "body": dict}`` so the
        Flask route can translate it to a real HTTP response.
        """
        if not self.integration or not self.integration.is_active:
            return {"status": 200, "body": {"ok": False, "error": "Integration not configured"}}

        signature = (headers or {}).get("X-Hub-Signature-256") or (headers or {}).get("x-hub-signature-256")
        event_type = (headers or {}).get("X-GitHub-Event") or (headers or {}).get("x-github-event") or ""

        secret = self._webhook_secret()
        if not secret:
            return {"status": 401, "body": {"ok": False, "error": "Webhook secret not configured"}}
        if not signature or not signature.startswith("sha256="):
            return {"status": 401, "body": {"ok": False, "error": "Missing or malformed signature"}}
        if raw_body is None:
            return {"status": 401, "body": {"ok": False, "error": "Raw body required for signature check"}}

        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature[7:], expected):
            logger.warning("GitHub webhook signature mismatch (event=%s)", event_type)
            return {"status": 401, "body": {"ok": False, "error": "Invalid signature"}}

        if event_type == "ping":
            return {"status": 200, "body": {"ok": True, "message": "Webhook received"}}
        if event_type != "issues":
            return {"status": 422, "body": {"ok": False, "error": f"Unhandled event: {event_type}"}}

        action = (payload or {}).get("action")
        issue = (payload or {}).get("issue") or {}
        if not action or not issue.get("number"):
            return {"status": 400, "body": {"ok": False, "error": "Malformed issue payload"}}

        if action == "opened":
            return self._handle_issue_opened(issue)
        if action == "assigned":
            return self._handle_issue_assigned(issue, payload.get("assignee") or issue.get("assignee") or {})
        if action == "closed":
            return self._handle_issue_closed(issue)

        return {"status": 422, "body": {"ok": False, "error": f"Unhandled action: {action}"}}

    # ------------------------------------------------------------------
    # Webhook event handlers
    # ------------------------------------------------------------------
    def _handle_issue_opened(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        from app import db
        from app.models import Task
        from app.utils.db import safe_commit

        cfg = self._cfg()
        project_id = cfg.get("default_project_id")
        if not project_id:
            return {"status": 200, "body": {"ok": False, "error": "default_project_id not set"}}

        number = issue.get("number")
        external_ref = f"github_issue_{number}"
        existing = Task.query.filter_by(project_id=int(project_id), external_ref=external_ref).first()
        if existing:
            return {"status": 200, "body": {"ok": True, "skipped": True, "task_id": existing.id}}

        try:
            task = self._build_task_from_issue(issue, int(project_id), external_ref)
            db.session.add(task)
            if not safe_commit("github_connector_webhook_open", {"issue": number}):
                return {"status": 200, "body": {"ok": False, "error": "Database error"}}
            return {"status": 200, "body": {"ok": True, "task_id": task.id}}
        except Exception as exc:
            logger.warning("Failed to create task for opened issue #%s: %s", number, exc)
            return {"status": 200, "body": {"ok": False, "error": str(exc)}}

    def _handle_issue_assigned(self, issue: Dict[str, Any], assignee: Dict[str, Any]) -> Dict[str, Any]:
        from app.models import User

        cfg = self._cfg()
        if not cfg.get("auto_start_timer"):
            return {"status": 200, "body": {"ok": True, "skipped": "auto_start_timer disabled"}}

        github_login = (assignee or {}).get("login")
        if not github_login:
            return {"status": 200, "body": {"ok": True, "skipped": "no assignee login"}}

        user = User.query.filter(User.github_username.ilike(github_login)).first()
        if not user:
            return {
                "status": 200,
                "body": {"ok": True, "skipped": f"no TimeTracker user mapped to '{github_login}'"},
            }

        project_id = cfg.get("default_project_id")
        if not project_id:
            return {"status": 200, "body": {"ok": False, "error": "default_project_id not set"}}

        try:
            from app.services.time_tracking_service import TimeTrackingService

            result = TimeTrackingService().start_timer(
                user_id=user.id,
                project_id=int(project_id),
                notes=f"GitHub issue #{issue.get('number')}: {(issue.get('title') or '')[:160]}",
            )
            return {"status": 200, "body": {"ok": bool(result.get("success")), "result": result.get("message")}}
        except Exception as exc:
            logger.warning("Auto-start timer for %s failed: %s", github_login, exc)
            return {"status": 200, "body": {"ok": False, "error": str(exc)}}

    def _handle_issue_closed(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        from app.models import Task
        from app.utils.db import safe_commit

        number = issue.get("number")
        external_ref = f"github_issue_{number}"
        task = Task.query.filter_by(external_ref=external_ref).first()
        if not task:
            return {"status": 200, "body": {"ok": True, "skipped": "task not found"}}
        task.status = "done"
        if not safe_commit("github_connector_webhook_close", {"issue": number}):
            return {"status": 200, "body": {"ok": False, "error": "Database error"}}
        return {"status": 200, "body": {"ok": True, "task_id": task.id}}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"token {self._token()}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "TimeTracker-GitHubConnector",
        }

    def _build_task_from_issue(self, issue: Dict[str, Any], project_id: int, external_ref: str):
        from app.models import Task

        title = (issue.get("title") or "Issue").strip()[:200]
        body = (issue.get("body") or "").strip()[:2000]
        labels = [(lbl.get("name") or "").lower() for lbl in (issue.get("labels") or [])]
        priority = "low"
        for label in labels:
            if label in _LABEL_PRIORITY:
                priority = _LABEL_PRIORITY[label]
                break

        creator_id = self.integration.user_id if self.integration and self.integration.user_id else None
        task = Task(
            project_id=project_id,
            name=title,
            description=body or None,
            status="todo",
            priority=priority,
            created_by=creator_id or self._fallback_admin_id(),
        )
        task.external_ref = external_ref
        return task

    @staticmethod
    def _fallback_admin_id() -> int:
        """Return any admin user id (used when the integration row has no owner)."""
        from app.models import User

        admin = User.query.filter_by(role="admin").first()
        return int(admin.id) if admin else 1

    # ------------------------------------------------------------------
    # Convenience class methods used by routes
    # ------------------------------------------------------------------
    @classmethod
    def for_user(cls, user) -> Optional["GitHubConnector"]:
        """Return a connector bound to ``user``'s GitHub integration, or None."""
        from app.models import Integration

        integration = (
            Integration.query.filter_by(provider=PROVIDER_KEY, user_id=getattr(user, "id", None)).first()
            if user
            else None
        )
        if not integration:
            return None
        return cls(integration=integration, credentials=None)

    @classmethod
    def for_any_active(cls) -> List["GitHubConnector"]:
        """Return one connector per active GitHub integration (any user)."""
        from app.models import Integration

        rows = Integration.query.filter_by(provider=PROVIDER_KEY, is_active=True).all()
        return [cls(integration=row, credentials=None) for row in rows]
