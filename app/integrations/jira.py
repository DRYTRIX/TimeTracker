"""
Jira integration connector.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os


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

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Sync issues from Jira and create tasks."""
        from app.models import Task, Project
        from app import db
        from datetime import datetime, timedelta

        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        base_url = self.integration.config.get("jira_url", "https://your-domain.atlassian.net")
        api_url = f"{base_url}/rest/api/3/search"
        
        synced_count = 0
        errors = []

        try:
            # Get JQL query from config or use default
            jql = self.integration.config.get("jql", "assignee = currentUser() AND status != Done ORDER BY updated DESC")
            
            # Determine date range
            if sync_type == "incremental":
                # Get issues updated in last 7 days
                jql = f"{jql} AND updated >= -7d"
            
            # Fetch issues from Jira
            response = requests.get(
                api_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json"
                },
                params={
                    "jql": jql,
                    "maxResults": 100,
                    "fields": "summary,description,status,assignee,project,created,updated"
                }
            )

            if response.status_code != 200:
                return {"success": False, "message": f"Jira API returned status {response.status_code}"}

            issues = response.json().get("issues", [])

            for issue in issues:
                try:
                    issue_key = issue.get("key")
                    issue_fields = issue.get("fields", {})
                    project_key = issue.get("fields", {}).get("project", {}).get("key", "")
                    
                    # Find or create project
                    project = Project.query.filter_by(
                        user_id=self.integration.user_id,
                        name=project_key or "Jira"
                    ).first()
                    
                    if not project:
                        project = Project(
                            name=project_key or "Jira",
                            description=f"Synced from Jira project {project_key}",
                            user_id=self.integration.user_id,
                            status="active"
                        )
                        db.session.add(project)
                        db.session.flush()

                    # Find or create task
                    task = Task.query.filter_by(
                        project_id=project.id,
                        name=issue_key
                    ).first()

                    if not task:
                        task = Task(
                            project_id=project.id,
                            name=issue_key,
                            description=issue_fields.get("summary", ""),
                            status=self._map_jira_status(issue_fields.get("status", {}).get("name", "To Do")),
                            notes=issue_fields.get("description", {}).get("content", [{}])[0].get("content", [{}])[0].get("text", "") if issue_fields.get("description") else None
                        )
                        db.session.add(task)
                        db.session.flush()

                    # Store Jira issue key in task metadata
                    if not hasattr(task, 'metadata') or not task.metadata:
                        task.metadata = {}
                    task.metadata['jira_issue_key'] = issue_key
                    task.metadata['jira_issue_id'] = issue.get("id")

                    synced_count += 1
                except Exception as e:
                    errors.append(f"Error syncing issue {issue.get('key', 'unknown')}: {str(e)}")

            db.session.commit()

            return {
                "success": True,
                "message": f"Sync completed. Synced {synced_count} issues.",
                "synced_items": synced_count,
                "errors": errors
            }
        except Exception as e:
            return {"success": False, "message": f"Sync failed: {str(e)}"}

    def _map_jira_status(self, jira_status: str) -> str:
        """Map Jira status to TimeTracker task status."""
        status_map = {
            "To Do": "todo",
            "In Progress": "in_progress",
            "Done": "completed",
            "Closed": "completed",
        }
        return status_map.get(jira_status, "todo")

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Handle incoming webhook from Jira."""
        try:
            event_type = payload.get("webhookEvent")
            issue = payload.get("issue", {})
            issue_key = issue.get("key")

            if not issue_key:
                return {"success": False, "message": "No issue key in webhook payload"}

            # Handle issue updated events
            if event_type in ["jira:issue_updated", "jira:issue_created"]:
                # Trigger a sync for this specific issue
                # This would be handled by the sync_data method
                return {
                    "success": True,
                    "message": f"Webhook received for issue {issue_key}",
                    "event_type": event_type
                }

            return {"success": True, "message": f"Webhook processed: {event_type}"}
        except Exception as e:
            return {"success": False, "message": f"Error processing webhook: {str(e)}"}

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
                },
                {
                    "name": "jql",
                    "label": "JQL Query",
                    "type": "text",
                    "required": False,
                    "placeholder": "assignee = currentUser() AND status != Done",
                    "help": "Jira Query Language query to filter issues to sync"
                },
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": True,
                    "description": "Automatically sync when webhooks are received"
                }
            ],
            "required": ["jira_url"],
        }
