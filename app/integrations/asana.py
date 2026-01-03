"""
Asana integration connector.
Sync tasks and projects with Asana.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os


def _env_if_allowed(name: str) -> str:
    """Prevent global env fallbacks for tenant-scoped credentials in SaaS multi-tenant mode."""
    try:
        from flask import current_app

        if bool(current_app.config.get("SAAS_MODE")) and (current_app.config.get("TENANCY_MODE") == "multi"):
            return ""
    except Exception:
        pass
    return os.getenv(name) or ""


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
        client_id = creds.get("client_id") or _env_if_allowed("ASANA_CLIENT_ID")

        if not client_id:
            raise ValueError("ASANA_CLIENT_ID not configured")

        auth_url = "https://app.asana.com/-/oauth_authorize"

        params = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "state": state or ""}

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("asana")
        client_id = creds.get("client_id") or _env_if_allowed("ASANA_CLIENT_ID")
        client_secret = creds.get("client_secret") or _env_if_allowed("ASANA_CLIENT_SECRET")

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
                    f"{self.BASE_URL}/users/me", headers={"Authorization": f"Bearer {data['access_token']}"}
                )
                if user_response.status_code == 200:
                    user_data = user_response.json().get("data", {})
                    user_info = {
                        "gid": user_data.get("gid"),
                        "name": user_data.get("name"),
                        "email": user_data.get("email"),
                    }
            except Exception as e:
                # Log error but don't fail - user info is optional
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Could not fetch Asana user info: {e}")

        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "token_type": "Bearer",
            "extra_data": user_info,
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token."""
        if not self.credentials or not self.credentials.refresh_token:
            raise ValueError("No refresh token available")

        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("asana")
        client_id = creds.get("client_id") or _env_if_allowed("ASANA_CLIENT_ID")
        client_secret = creds.get("client_secret") or _env_if_allowed("ASANA_CLIENT_SECRET")

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

        return {"access_token": data.get("access_token"), "expires_at": expires_at.isoformat() if expires_at else None}

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Asana."""
        try:
            headers = {"Authorization": f"Bearer {self.get_access_token()}"}
            response = requests.get(f"{self.BASE_URL}/users/me", headers=headers)

            if response.status_code == 200:
                user_data = response.json().get("data", {})
                return {"success": True, "message": f"Connected to Asana as {user_data.get('name', 'Unknown')}"}
            else:
                return {"success": False, "message": f"Connection test failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {str(e)}"}

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
                params={"workspace": workspace_gid, "opt_fields": "name,notes,archived"},
            )

            if projects_response.status_code == 200:
                asana_projects = projects_response.json().get("data", [])

                for asana_project in asana_projects:
                    try:
                        # Find or create project
                        project = Project.query.filter_by(
                            user_id=self.integration.user_id, name=asana_project.get("name")
                        ).first()

                        if not project:
                            project = Project(
                                name=asana_project.get("name"),
                                description=asana_project.get("notes", ""),
                                user_id=self.integration.user_id,
                                status="active" if not asana_project.get("archived") else "archived",
                            )
                            db.session.add(project)
                            db.session.flush()

                        # Store Asana project GID in project metadata
                        if not hasattr(project, "metadata") or not project.metadata:
                            project.metadata = {}
                        project.metadata["asana_project_gid"] = asana_project.get("gid")

                        # Sync tasks from Asana project
                        tasks_response = requests.get(
                            f"{self.BASE_URL}/projects/{asana_project.get('gid')}/tasks",
                            headers=headers,
                            params={"opt_fields": "name,notes,completed,due_on"},
                        )

                        if tasks_response.status_code == 200:
                            asana_tasks = tasks_response.json().get("data", [])

                            for asana_task in asana_tasks:
                                try:
                                    # Get task details
                                    task_response = requests.get(
                                        f"{self.BASE_URL}/tasks/{asana_task.get('gid')}",
                                        headers=headers,
                                        params={"opt_fields": "name,notes,completed,due_on,assignee"},
                                    )

                                    if task_response.status_code == 200:
                                        task_data = task_response.json().get("data", {})

                                        # Find or create task
                                        task = Task.query.filter_by(
                                            project_id=project.id, name=task_data.get("name", "")
                                        ).first()

                                        if not task:
                                            task = Task(
                                                project_id=project.id,
                                                name=task_data.get("name", ""),
                                                description=task_data.get("notes", ""),
                                                status="completed" if task_data.get("completed") else "todo",
                                            )
                                            db.session.add(task)
                                            db.session.flush()

                                        # Store Asana task GID in metadata
                                        if not hasattr(task, "metadata") or not task.metadata:
                                            task.metadata = {}
                                        task.metadata["asana_task_gid"] = asana_task.get("gid")
                                except Exception as e:
                                    errors.append(
                                        f"Error syncing task in project {asana_project.get('name')}: {str(e)}"
                                    )

                        synced_count += 1
                    except Exception as e:
                        errors.append(f"Error syncing project {asana_project.get('name')}: {str(e)}")

            db.session.commit()

            return {"success": True, "synced_count": synced_count, "errors": errors}

        except Exception as e:
            return {"success": False, "message": f"Sync failed: {str(e)}"}

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "workspace_gid",
                    "type": "string",
                    "label": "Workspace GID",
                    "required": True,
                    "placeholder": "1234567890",
                    "description": "Asana workspace GID to sync with",
                    "help": "Find your workspace GID in Asana workspace settings or API",
                },
                {
                    "name": "project_gids",
                    "type": "text",
                    "label": "Project GIDs",
                    "required": False,
                    "placeholder": "1234567890, 9876543210",
                    "description": "Comma-separated list of specific project GIDs to sync (leave empty to sync all)",
                    "help": "Optional: Limit sync to specific projects",
                },
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "asana_to_timetracker", "label": "Asana → TimeTracker (Import only)"},
                        {"value": "timetracker_to_asana", "label": "TimeTracker → Asana (Export only)"},
                        {"value": "bidirectional", "label": "Bidirectional (Two-way sync)"},
                    ],
                    "default": "asana_to_timetracker",
                    "description": "Choose how data flows between Asana and TimeTracker",
                },
                {
                    "name": "sync_items",
                    "type": "array",
                    "label": "Items to Sync",
                    "options": [
                        {"value": "projects", "label": "Projects"},
                        {"value": "tasks", "label": "Tasks"},
                        {"value": "subtasks", "label": "Subtasks"},
                    ],
                    "default": ["projects", "tasks"],
                    "description": "Select which items to synchronize",
                },
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": False,
                    "description": "Automatically sync when changes are detected",
                },
                {
                    "name": "sync_interval",
                    "type": "select",
                    "label": "Sync Schedule",
                    "options": [
                        {"value": "manual", "label": "Manual only"},
                        {"value": "hourly", "label": "Every hour"},
                        {"value": "daily", "label": "Daily"},
                    ],
                    "default": "manual",
                    "description": "How often to automatically sync data",
                },
                {
                    "name": "sync_completed",
                    "type": "boolean",
                    "label": "Sync Completed Tasks",
                    "default": False,
                    "description": "Include completed tasks in sync",
                },
                {
                    "name": "status_mapping",
                    "type": "json",
                    "label": "Status Mapping",
                    "placeholder": '{"completed": "completed", "incomplete": "todo"}',
                    "description": "Map Asana task completion status to TimeTracker statuses (JSON format)",
                    "help": "Customize how Asana task statuses map to TimeTracker task statuses",
                },
            ],
            "required": ["workspace_gid"],
            "sections": [
                {
                    "title": "Workspace Settings",
                    "description": "Configure your Asana workspace",
                    "fields": ["workspace_gid", "project_gids"],
                },
                {
                    "title": "Sync Settings",
                    "description": "Configure what and how to sync",
                    "fields": ["sync_direction", "sync_items", "sync_completed", "auto_sync", "sync_interval"],
                },
                {
                    "title": "Data Mapping",
                    "description": "Customize how data translates between Asana and TimeTracker",
                    "fields": ["status_mapping"],
                },
            ],
            "sync_settings": {
                "enabled": True,
                "auto_sync": False,
                "sync_interval": "manual",
                "sync_direction": "asana_to_timetracker",
                "sync_items": ["projects", "tasks"],
            },
        }
