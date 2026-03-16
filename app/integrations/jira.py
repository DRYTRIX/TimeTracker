"""
Jira integration connector.
"""

import hashlib
import hmac
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import requests

from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)

# Jira issue key format: PROJECT_KEY-NUMBER (e.g. PROJ-123, MYPROJ-1)
JIRA_ISSUE_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]+-[0-9]+$")


class JiraConnector(BaseConnector):
    """Jira integration connector."""

    display_name = "Jira"
    description = "Sync issues and track time in Jira"
    icon = "jira"

    @property
    def provider_name(self) -> str:
        return "jira"

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Get Jira OAuth authorization URL."""
        # Jira uses OAuth 2.0
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("jira")
        client_id = creds.get("client_id") or os.getenv("JIRA_CLIENT_ID")
        if not client_id:
            raise ValueError("JIRA_CLIENT_ID not configured")

        base_url = self.integration.config.get("jira_url", "https://your-domain.atlassian.net")
        auth_url = f"{base_url}/plugins/servlet/oauth/authorize"

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "read:jira-work write:jira-work offline_access",
            "state": state or "",
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("jira")
        client_id = creds.get("client_id") or os.getenv("JIRA_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("JIRA_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("Jira OAuth credentials not configured")

        base_url = self.integration.config.get("jira_url", "https://your-domain.atlassian.net")
        token_url = f"{base_url}/plugins/servlet/oauth/token"

        response = requests.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )

        response.raise_for_status()
        data = response.json()

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at,
            "token_type": data.get("token_type", "Bearer"),
            "scope": data.get("scope"),
            "extra_data": {"cloud_id": data.get("cloud_id"), "site_url": base_url},
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token."""
        if not self.credentials or not self.credentials.refresh_token:
            raise ValueError("No refresh token available")

        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("jira")
        client_id = creds.get("client_id") or os.getenv("JIRA_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("JIRA_CLIENT_SECRET")

        base_url = self.integration.config.get("jira_url", "https://your-domain.atlassian.net")
        token_url = f"{base_url}/plugins/servlet/oauth/token"

        response = requests.post(
            token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": self.credentials.refresh_token,
            },
        )

        response.raise_for_status()
        data = response.json()

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token", self.credentials.refresh_token),
            "expires_at": expires_at,
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Jira."""
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        base_url = self.integration.config.get("jira_url", "https://your-domain.atlassian.net")
        api_url = f"{base_url}/rest/api/3/myself"

        try:
            response = requests.get(api_url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})

            if response.status_code == 200:
                user_data = response.json()
                return {"success": True, "message": f"Connected as {user_data.get('displayName', 'Unknown')}"}
            else:
                return {"success": False, "message": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {str(e)}"}

    def _extract_description_text(self, issue_fields: Dict[str, Any]) -> Optional[str]:
        """Extract plain text from Jira description (ADF content structure)."""
        desc = issue_fields.get("description")
        if not desc or not isinstance(desc, dict):
            return None
        try:
            content = desc.get("content") or []
            if content and isinstance(content[0], dict):
                inner = content[0].get("content") or []
                if inner and isinstance(inner[0], dict):
                    return inner[0].get("text") or None
        except (IndexError, KeyError, TypeError):
            pass
        return None

    def _upsert_task_from_issue(self, issue: Dict[str, Any]) -> int:
        """
        Find or create Project and Task from a single Jira issue dict.
        Reuses same mapping logic as sync_data. Returns 1 if upserted, 0 on skip/error.
        """
        from app import db
        from app.models import Project, Task

        issue_key = issue.get("key")
        if not issue_key:
            return 0
        issue_fields = issue.get("fields") or {}
        project_key = (issue_fields.get("project") or {}).get("key") or ""
        project_key = project_key or "Jira"

        project = Project.query.filter_by(
            user_id=self.integration.user_id, name=project_key
        ).first()

        if not project:
            project = Project(
                name=project_key,
                description=f"Synced from Jira project {project_key}",
                user_id=self.integration.user_id,
                status="active",
            )
            db.session.add(project)
            db.session.flush()

        task = Task.query.filter_by(project_id=project.id, name=issue_key).first()
        summary = issue_fields.get("summary") or ""
        status_name = (issue_fields.get("status") or {}).get("name") or "To Do"
        mapped_status = self._map_jira_status(status_name)
        description_text = self._extract_description_text(issue_fields)

        if not task:
            task_kw = {
                "project_id": project.id,
                "name": issue_key,
                "description": summary,
                "status": mapped_status,
            }
            if getattr(Task, "notes", None) is not None:
                task_kw["notes"] = description_text
            if self.integration.user_id is not None:
                task_kw["created_by"] = self.integration.user_id
            task = Task(**task_kw)
            db.session.add(task)
            db.session.flush()
        else:
            task.description = summary
            task.status = mapped_status
            if hasattr(task, "notes"):
                task.notes = description_text

        if hasattr(task, "metadata"):
            if not task.metadata:
                task.metadata = {}
            task.metadata["jira_issue_key"] = issue_key
            task.metadata["jira_issue_id"] = issue.get("id")

        return 1

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Sync issues from Jira and create tasks."""
        from app import db

        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        base_url = self.integration.config.get("jira_url", "https://your-domain.atlassian.net")
        api_url = f"{base_url}/rest/api/3/search"

        synced_count = 0
        errors = []

        try:
            jql = self.integration.config.get(
                "jql", "assignee = currentUser() AND status != Done ORDER BY updated DESC"
            )
            if sync_type == "incremental":
                jql = f"{jql} AND updated >= -7d"

            response = requests.get(
                api_url,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                params={
                    "jql": jql,
                    "maxResults": 100,
                    "fields": "summary,description,status,assignee,project,created,updated",
                },
            )

            if response.status_code != 200:
                return {"success": False, "message": f"Jira API returned status {response.status_code}"}

            issues = response.json().get("issues", [])

            for issue in issues:
                try:
                    synced_count += self._upsert_task_from_issue(issue)
                except Exception as e:
                    errors.append(f"Error syncing issue {issue.get('key', 'unknown')}: {str(e)}")

            db.session.commit()

            return {
                "success": True,
                "message": f"Sync completed. Synced {synced_count} issues.",
                "synced_items": synced_count,
                "errors": errors,
            }
        except Exception as e:
            return {"success": False, "message": f"Sync failed: {str(e)}"}

    def sync_issue(self, issue_key: str) -> Dict[str, Any]:
        """
        Fetch a single Jira issue by key and upsert it as a task.
        Idempotent: repeated calls for the same issue_key just update the task.
        """
        from app import db

        if not issue_key or not isinstance(issue_key, str):
            return {"success": False, "message": "Invalid issue key", "issue_key": issue_key}
        issue_key = issue_key.strip()
        if not JIRA_ISSUE_KEY_PATTERN.match(issue_key):
            return {
                "success": False,
                "message": "Invalid issue key format (expected PROJECT-NUM)",
                "issue_key": issue_key,
            }

        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available", "issue_key": issue_key}

        base_url = self.integration.config.get("jira_url", "https://your-domain.atlassian.net")
        api_url = f"{base_url}/rest/api/3/issue/{issue_key}"
        fields = "summary,description,status,assignee,project,created,updated"

        try:
            response = requests.get(
                api_url,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                params={"fields": fields},
            )

            if response.status_code == 404:
                return {
                    "success": False,
                    "message": "Issue not found",
                    "issue_key": issue_key,
                }
            if response.status_code != 200:
                body = response.text[:500] if response.text else ""
                return {
                    "success": False,
                    "message": f"Jira API returned status {response.status_code}",
                    "issue_key": issue_key,
                    "status_code": response.status_code,
                    "detail": body,
                }

            issue = response.json()
            self._upsert_task_from_issue(issue)
            db.session.commit()
            return {
                "success": True,
                "synced_items": 1,
                "issue_key": issue_key,
            }
        except Exception as e:
            logger.exception("sync_issue failed for %s: %s", issue_key, e)
            try:
                db.session.rollback()
            except Exception:
                pass
            return {
                "success": False,
                "message": str(e),
                "issue_key": issue_key,
            }

    def _map_jira_status(self, jira_status: str) -> str:
        """Map Jira status to TimeTracker task status."""
        # Check for custom status mapping in config
        status_mapping = self.get_status_mappings()
        if status_mapping and jira_status in status_mapping:
            return status_mapping[jira_status]

        # Default mapping
        status_map = {
            "To Do": "todo",
            "In Progress": "in_progress",
            "Done": "completed",
            "Closed": "completed",
        }
        return status_map.get(jira_status, "todo")

    def handle_webhook(
        self, payload: Dict[str, Any], headers: Dict[str, str], raw_body: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """Handle incoming webhook from Jira. Validates payload and triggers issue-specific sync when appropriate."""
        if not isinstance(payload, dict):
            logger.warning("Jira webhook invalid payload: expected JSON object")
            return {"success": False, "message": "Invalid webhook payload"}

        # Optional webhook signature verification (Jira Cloud uses HMAC-SHA256; WebSub-style X-Hub-Signature)
        webhook_secret = self.integration.config.get("webhook_secret") if self.integration else None
        if webhook_secret:
            signature = (
                headers.get("X-Hub-Signature-256")
                or headers.get("X-Atlassian-Webhook-Signature")
                or headers.get("X-Hub-Signature")
                or ""
            ).strip()
            if not signature:
                logger.warning("Jira webhook secret configured but no signature provided - rejecting")
                return {"success": False, "message": "Webhook signature required"}
            # Normalize: accept "sha256=<hex>" or "method=value" (WebSub)
            if signature.startswith("sha256="):
                signature_hash = signature[7:]
            elif "=" in signature:
                signature_hash = signature.split("=", 1)[1].strip()
            else:
                signature_hash = signature
            if raw_body is None:
                raw_body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
                logger.debug("Jira webhook: using reconstructed body for signature verification")
            expected = hmac.new(webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature_hash, expected):
                logger.warning("Jira webhook signature verification failed")
                return {"success": False, "message": "Webhook signature verification failed"}

        event_type = payload.get("webhookEvent")
        if event_type is not None and not isinstance(event_type, str):
            event_type = str(event_type)

        issue = payload.get("issue")
        if not isinstance(issue, dict):
            logger.warning("Jira webhook missing or invalid issue object")
            return {"success": False, "message": "Missing or invalid issue in webhook payload"}

        raw_key = issue.get("key")
        issue_key = (raw_key if isinstance(raw_key, str) else "").strip()
        if not issue_key:
            logger.warning("Jira webhook missing or empty issue key")
            return {"success": False, "message": "No issue key in webhook payload"}

        if not JIRA_ISSUE_KEY_PATTERN.match(issue_key):
            logger.warning("Jira webhook invalid issue key format: %s", issue_key)
            return {
                "success": False,
                "message": "Invalid issue key format in webhook payload",
                "issue_key": issue_key,
            }

        supported_events = ("jira:issue_updated", "jira:issue_created")
        if event_type not in supported_events:
            logger.info(
                "Jira webhook event ignored: event_type=%s issue_key=%s",
                event_type,
                issue_key,
            )
            return {
                "success": True,
                "message": f"Event ignored: {event_type or 'unknown'}",
                "event_type": event_type or "unknown",
                "issue_key": issue_key,
            }

        auto_sync = self.get_sync_settings().get("auto_sync", False)
        if not auto_sync:
            logger.info(
                "Jira webhook acknowledged (auto_sync disabled): event_type=%s issue_key=%s",
                event_type,
                issue_key,
            )
            return {
                "success": True,
                "message": f"Webhook received for issue {issue_key}",
                "event_type": event_type,
                "issue_key": issue_key,
            }

        try:
            sync_result = self.sync_issue(issue_key)
            if sync_result.get("success"):
                logger.info(
                    "Jira webhook sync ok: event_type=%s issue_key=%s",
                    event_type,
                    issue_key,
                )
                return {
                    "success": True,
                    "message": f"Synced issue {issue_key}",
                    "event_type": event_type,
                    "issue_key": issue_key,
                    "synced_items": sync_result.get("synced_items", 1),
                }
            msg = sync_result.get("message", "Sync failed")
            logger.warning(
                "Jira webhook sync failed: event_type=%s issue_key=%s reason=%s",
                event_type,
                issue_key,
                msg,
            )
            return {
                "success": False,
                "message": msg,
                "event_type": event_type,
                "issue_key": issue_key,
            }
        except Exception as e:
            logger.exception(
                "Jira webhook sync error: event_type=%s issue_key=%s error=%s",
                event_type,
                issue_key,
                e,
            )
            return {
                "success": False,
                "message": str(e),
                "event_type": event_type,
                "issue_key": issue_key,
            }

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "jira_url",
                    "label": "Jira URL",
                    "type": "url",
                    "required": True,
                    "placeholder": "https://your-domain.atlassian.net",
                    "description": "Your Jira instance URL",
                    "help": "Enter your Jira Cloud or Server URL",
                },
                {
                    "name": "jql",
                    "label": "JQL Query",
                    "type": "text",
                    "required": False,
                    "placeholder": "assignee = currentUser() AND status != Done ORDER BY updated DESC",
                    "help": "Jira Query Language query to filter issues to sync. Leave empty to sync all assigned issues.",
                    "description": "Filter which issues to sync from Jira",
                },
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "jira_to_timetracker", "label": "Jira → TimeTracker (Import only)"},
                        {"value": "timetracker_to_jira", "label": "TimeTracker → Jira (Export only)"},
                        {"value": "bidirectional", "label": "Bidirectional (Two-way sync)"},
                    ],
                    "default": "jira_to_timetracker",
                    "description": "Choose how data flows between Jira and TimeTracker",
                },
                {
                    "name": "sync_items",
                    "type": "array",
                    "label": "Items to Sync",
                    "options": [
                        {"value": "issues", "label": "Issues (Tasks)"},
                        {"value": "projects", "label": "Projects"},
                        {"value": "time_entries", "label": "Time Entries"},
                    ],
                    "default": ["issues"],
                    "description": "Select which items to synchronize",
                },
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": False,
                    "description": "Automatically sync when webhooks are received from Jira",
                },
                {
                    "name": "sync_interval",
                    "type": "select",
                    "label": "Sync Schedule",
                    "options": [
                        {"value": "manual", "label": "Manual only"},
                        {"value": "hourly", "label": "Every hour"},
                        {"value": "daily", "label": "Daily"},
                        {"value": "weekly", "label": "Weekly"},
                    ],
                    "default": "manual",
                    "description": "How often to automatically sync data",
                },
                {
                    "name": "create_projects",
                    "type": "boolean",
                    "label": "Create Projects",
                    "default": True,
                    "description": "Automatically create projects in TimeTracker from Jira projects",
                },
                {
                    "name": "status_mapping",
                    "type": "json",
                    "label": "Status Mapping",
                    "placeholder": '{"To Do": "todo", "In Progress": "in_progress", "Done": "completed"}',
                    "description": "Map Jira statuses to TimeTracker statuses (JSON format)",
                    "help": "Customize how Jira issue statuses map to TimeTracker task statuses",
                },
                {
                    "name": "field_mapping",
                    "type": "json",
                    "label": "Field Mapping",
                    "placeholder": '{"summary": "name", "description": "description", "assignee": "user_id"}',
                    "description": "Map Jira fields to TimeTracker fields (JSON format)",
                    "help": "Customize how Jira issue fields map to TimeTracker task fields",
                },
                {
                    "name": "webhook_secret",
                    "type": "password",
                    "label": "Webhook Secret",
                    "required": False,
                    "description": "Optional secret for verifying webhook requests (Jira Cloud: set in webhook config)",
                    "help": "When set, incoming webhooks must include a valid signature (HMAC-SHA256 of body). Leave empty to accept all webhooks.",
                },
            ],
            "required": ["jira_url"],
            "sections": [
                {
                    "title": "Connection Settings",
                    "description": "Configure your Jira connection",
                    "fields": ["jira_url", "jql", "webhook_secret"],
                },
                {
                    "title": "Sync Settings",
                    "description": "Configure what and how to sync",
                    "fields": ["sync_direction", "sync_items", "auto_sync", "sync_interval", "create_projects"],
                },
                {
                    "title": "Data Mapping",
                    "description": "Customize how data translates between Jira and TimeTracker",
                    "fields": ["status_mapping", "field_mapping"],
                },
            ],
            "sync_settings": {
                "enabled": True,
                "auto_sync": False,
                "sync_interval": "manual",
                "sync_direction": "jira_to_timetracker",
                "sync_items": ["issues"],
            },
        }
