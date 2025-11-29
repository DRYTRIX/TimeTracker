"""
GitLab integration connector.
Sync issues and track time from GitLab.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os


class GitLabConnector(BaseConnector):
    """GitLab integration connector."""

    display_name = "GitLab"
    description = "Sync issues and track time from GitLab"
    icon = "gitlab"

    @property
    def provider_name(self) -> str:
        return "gitlab"

    def _get_base_url(self) -> str:
        """Get GitLab instance URL from settings."""
        from app.models import Settings
        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("gitlab")
        instance_url = creds.get("instance_url") or os.getenv("GITLAB_INSTANCE_URL", "https://gitlab.com")
        return instance_url.rstrip("/")

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Get GitLab OAuth authorization URL."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("gitlab")
        client_id = creds.get("client_id") or os.getenv("GITLAB_CLIENT_ID")
        base_url = self._get_base_url()

        if not client_id:
            raise ValueError("GITLAB_CLIENT_ID not configured")

        scopes = ["api", "read_user", "read_repository", "write_repository"]

        auth_url = f"{base_url}/oauth/authorize"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state or "",
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("gitlab")
        client_id = creds.get("client_id") or os.getenv("GITLAB_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("GITLAB_CLIENT_SECRET")
        base_url = self._get_base_url()

        if not client_id or not client_secret:
            raise ValueError("GitLab OAuth credentials not configured")

        token_url = f"{base_url}/oauth/token"

        response = requests.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )

        response.raise_for_status()
        data = response.json()

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        # Get user info
        user_info = {}
        if "access_token" in data:
            try:
                user_response = requests.get(
                    f"{base_url}/api/v4/user",
                    headers={"Authorization": f"Bearer {data['access_token']}"}
                )
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    user_info = {
                        "id": user_data.get("id"),
                        "username": user_data.get("username"),
                        "name": user_data.get("name"),
                        "email": user_data.get("email"),
                    }
            except Exception:
                pass

        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "token_type": data.get("token_type", "Bearer"),
            "scope": data.get("scope"),
            "extra_data": user_info,
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token."""
        if not self.credentials or not self.credentials.refresh_token:
            raise ValueError("No refresh token available")

        from app.models import Settings
        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("gitlab")
        client_id = creds.get("client_id") or os.getenv("GITLAB_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("GITLAB_CLIENT_SECRET")
        base_url = self._get_base_url()

        token_url = f"{base_url}/oauth/token"

        response = requests.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": self.credentials.refresh_token,
                "grant_type": "refresh_token",
            },
        )

        response.raise_for_status()
        data = response.json()

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        # Update credentials
        self.credentials.access_token = data.get("access_token")
        if "refresh_token" in data:
            self.credentials.refresh_token = data.get("refresh_token")
        if expires_at:
            self.credentials.expires_at = expires_at
        from app.utils.db import safe_commit
        safe_commit("refresh_gitlab_token", {"integration_id": self.integration.id})

        return {
            "access_token": data.get("access_token"),
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to GitLab."""
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        base_url = self._get_base_url()
        api_url = f"{base_url}/api/v4/user"

        try:
            response = requests.get(
                api_url,
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                user_data = response.json()
                return {"success": True, "message": f"Connected as {user_data.get('username', 'Unknown')}"}
            else:
                return {"success": False, "message": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {str(e)}"}

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Sync issues from GitLab repositories."""
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        base_url = self._get_base_url()
        synced_count = 0
        errors = []

        try:
            # Get repositories from config or all accessible repos
            repo_ids = self.integration.config.get("repository_ids", [])
            
            if not repo_ids:
                # Get all accessible projects
                projects_response = requests.get(
                    f"{base_url}/api/v4/projects",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"membership": True, "per_page": 100}
                )
                if projects_response.status_code == 200:
                    projects = projects_response.json()
                    repo_ids = [p["id"] for p in projects]

            # Sync issues from each repository
            for repo_id in repo_ids:
                try:
                    issues_response = requests.get(
                        f"{base_url}/api/v4/projects/{repo_id}/issues",
                        headers={"Authorization": f"Bearer {token}"},
                        params={"state": "opened", "per_page": 100}
                    )
                    
                    if issues_response.status_code == 200:
                        issues = issues_response.json()
                        synced_count += len(issues)
                except Exception as e:
                    errors.append(f"Error syncing repository {repo_id}: {str(e)}")

            return {
                "success": True,
                "message": "Sync completed",
                "synced_items": synced_count,
                "errors": errors
            }
        except Exception as e:
            return {"success": False, "message": f"Sync failed: {str(e)}"}

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "repository_ids",
                    "type": "array",
                    "label": "Repository IDs",
                    "description": "GitLab project IDs to sync (leave empty to sync all accessible projects)"
                },
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "gitlab_to_timetracker", "label": "GitLab → TimeTracker"},
                        {"value": "timetracker_to_gitlab", "label": "TimeTracker → GitLab"},
                        {"value": "bidirectional", "label": "Bidirectional"}
                    ],
                    "default": "gitlab_to_timetracker"
                }
            ],
            "required": []
        }

