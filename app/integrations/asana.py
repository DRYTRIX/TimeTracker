"""
Asana integration connector.
Sync tasks and projects with Asana.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os


class AsanaConnector(BaseConnector):
    """Asana integration connector."""

    display_name = "Asana"
    description = "Sync tasks and projects with Asana"
    icon = "asana"

    BASE_URL = "https://app.asana.com/api/1.0"

    @property
    def provider_name(self) -> str:
        return "asana"

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Get Asana OAuth authorization URL."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("asana")
        client_id = creds.get("client_id") or os.getenv("ASANA_CLIENT_ID")

        if not client_id:
            raise ValueError("ASANA_CLIENT_ID not configured")

        auth_url = "https://app.asana.com/-/oauth_authorize"
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state or ""
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("asana")
        client_id = creds.get("client_id") or os.getenv("ASANA_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("ASANA_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("Asana OAuth credentials not configured")

        token_url = f"{self.BASE_URL}/oauth_token"

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

        # Get user info
        user_info = {}
        if "access_token" in data:
            try:
                user_response = requests.get(
                    f"{self.BASE_URL}/users/me",
                    headers={"Authorization": f"Bearer {data['access_token']}"}
                )
                if user_response.status_code == 200:
                    user_data = user_response.json().get("data", {})
                    user_info = {
                        "gid": user_data.get("gid"),
                        "name": user_data.get("name"),
                        "email": user_data.get("email")
                    }
            except Exception:
                pass

        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "token_type": "Bearer",
            "extra_data": user_info
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token."""
        if not self.credentials or not self.credentials.refresh_token:
            raise ValueError("No refresh token available")

        from app.models import Settings
        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("asana")
        client_id = creds.get("client_id") or os.getenv("ASANA_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("ASANA_CLIENT_SECRET")

        token_url = f"{self.BASE_URL}/oauth_token"

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

        # Update credentials
        self.credentials.access_token = data.get("access_token")
        if "refresh_token" in data:
            self.credentials.refresh_token = data.get("refresh_token")
        if expires_at:
            self.credentials.expires_at = expires_at
        self.credentials.save()

        return {
            "access_token": data.get("access_token"),
            "expires_at": expires_at.isoformat() if expires_at else None
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Asana."""
        try:
            headers = {"Authorization": f"Bearer {self.get_access_token()}"}
            response = requests.get(f"{self.BASE_URL}/users/me", headers=headers)
            
            if response.status_code == 200:
                user_data = response.json().get("data", {})
                return {
                    "success": True,
                    "message": f"Connected to Asana as {user_data.get('name', 'Unknown')}"
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection test failed: {response.status_code}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}"
            }

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Sync tasks and projects with Asana."""
        from app.models import Task, Project
        from app import db

        try:
            headers = {"Authorization": f"Bearer {self.get_access_token()}"}
            
            # Get workspace from config
            workspace_gid = self.integration.config.get("workspace_gid")
            if not workspace_gid:
                return {"success": False, "message": "Workspace GID not configured"}

            synced_count = 0
            errors = []

            # Sync projects from Asana
            projects_response = requests.get(
                f"{self.BASE_URL}/projects",
                headers=headers,
                params={"workspace": workspace_gid, "opt_fields": "name,notes,archived"}
            )

            if projects_response.status_code == 200:
                asana_projects = projects_response.json().get("data", [])

                for asana_project in asana_projects:
                    try:
                        # Find or create project
                        project = Project.query.filter_by(
                            user_id=self.integration.user_id,
                            name=asana_project.get("name")
                        ).first()

                        if not project:
                            project = Project(
                                name=asana_project.get("name"),
                                description=asana_project.get("notes", ""),
                                user_id=self.integration.user_id,
                                status="active" if not asana_project.get("archived") else "archived"
                            )
                            db.session.add(project)
                            db.session.flush()

                        # Store Asana project GID in project metadata
                        if not hasattr(project, 'metadata') or not project.metadata:
                            project.metadata = {}
                        project.metadata['asana_project_gid'] = asana_project.get("gid")
                        
                        synced_count += 1
                    except Exception as e:
                        errors.append(f"Error syncing project {asana_project.get('name')}: {str(e)}")

            db.session.commit()

            return {
                "success": True,
                "synced_count": synced_count,
                "errors": errors
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Sync failed: {str(e)}"
            }

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "workspace_gid",
                    "type": "string",
                    "label": "Workspace GID",
                    "description": "Asana workspace GID to sync with"
                },
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "asana_to_timetracker", "label": "Asana → TimeTracker"},
                        {"value": "timetracker_to_asana", "label": "TimeTracker → Asana"},
                        {"value": "bidirectional", "label": "Bidirectional"}
                    ],
                    "default": "asana_to_timetracker"
                }
            ],
            "required": ["workspace_gid"]
        }

