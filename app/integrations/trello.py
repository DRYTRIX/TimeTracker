"""
Trello integration connector.
Sync boards, lists, and cards with Trello.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os
import hmac
import hashlib
import base64


class TrelloConnector(BaseConnector):
    """Trello integration connector."""

    display_name = "Trello"
    description = "Sync boards and cards with Trello"
    icon = "trello"

    BASE_URL = "https://api.trello.com/1"

    @property
    def provider_name(self) -> str:
        return "trello"

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Get Trello OAuth authorization URL."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("trello")
        api_key = creds.get("api_key") or os.getenv("TRELLO_API_KEY")

        if not api_key:
            raise ValueError("TRELLO_API_KEY not configured")

        auth_url = "https://trello.com/1/OAuthAuthorizeToken"

        params = {
            "key": api_key,
            "name": "TimeTracker Integration",
            "response_type": "token",
            "scope": "read,write",
            "expiration": "never",
            "redirect_uri": redirect_uri
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens (Trello uses token directly)."""
        # Trello uses token-based auth, not OAuth flow
        # The token is returned directly from the authorization URL
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("trello")
        api_key = creds.get("api_key") or os.getenv("TRELLO_API_KEY")

        if not api_key:
            raise ValueError("Trello API key not configured")

        # For Trello, the 'code' parameter is actually the token
        token = code

        # Verify token by getting user info
        user_info = {}
        try:
            response = requests.get(
                f"{self.BASE_URL}/members/me",
                params={"key": api_key, "token": token}
            )
            if response.status_code == 200:
                user_data = response.json()
                user_info = {
                    "id": user_data.get("id"),
                    "username": user_data.get("username"),
                    "fullName": user_data.get("fullName"),
                    "email": user_data.get("email")
                }
        except Exception:
            pass

        return {
            "access_token": token,
            "refresh_token": None,  # Trello tokens don't expire
            "expires_at": None,
            "token_type": "Bearer",
            "extra_data": user_info
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token (Trello tokens don't expire)."""
        # Trello tokens don't expire, so just return current token
        return {
            "access_token": self.credentials.access_token if self.credentials else None,
            "expires_at": None
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Trello."""
        try:
            from app.models import Settings
            settings = Settings.get_settings()
            creds = settings.get_integration_credentials("trello")
            api_key = creds.get("api_key") or os.getenv("TRELLO_API_KEY")

            headers = {"Authorization": f"Bearer {self.get_access_token()}"}
            response = requests.get(
                f"{self.BASE_URL}/members/me",
                params={"key": api_key, "token": self.get_access_token()}
            )

            if response.status_code == 200:
                user_data = response.json()
                return {
                    "success": True,
                    "message": f"Connected to Trello as {user_data.get('fullName', 'Unknown')}"
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
        """Sync boards and cards with Trello."""
        from app.models import Project, Task
        from app import db

        try:
            from app.models import Settings
            settings = Settings.get_settings()
            creds = settings.get_integration_credentials("trello")
            api_key = creds.get("api_key") or os.getenv("TRELLO_API_KEY")

            token = self.get_access_token()
            if not token or not api_key:
                return {"success": False, "message": "Trello credentials not configured"}

            synced_count = 0
            errors = []

            # Get boards
            boards_response = requests.get(
                f"{self.BASE_URL}/members/me/boards",
                params={"key": api_key, "token": token, "filter": "open"}
            )

            if boards_response.status_code == 200:
                boards = boards_response.json()

                for board in boards:
                    try:
                        # Create or update project from board
                        project = Project.query.filter_by(
                            user_id=self.integration.user_id,
                            name=board.get("name")
                        ).first()

                        if not project:
                            project = Project(
                                name=board.get("name"),
                                description=board.get("desc", ""),
                                user_id=self.integration.user_id,
                                status="active"
                            )
                            db.session.add(project)
                            db.session.flush()

                        # Store Trello board ID in metadata
                        if not hasattr(project, 'metadata') or not project.metadata:
                            project.metadata = {}
                        project.metadata['trello_board_id'] = board.get("id")

                        # Sync cards as tasks
                        cards_response = requests.get(
                            f"{self.BASE_URL}/boards/{board.get('id')}/cards",
                            params={"key": api_key, "token": token, "filter": "open"}
                        )

                        if cards_response.status_code == 200:
                            cards = cards_response.json()

                            for card in cards:
                                # Find or create task
                                task = Task.query.filter_by(
                                    project_id=project.id,
                                    name=card.get("name")
                                ).first()

                                if not task:
                                    task = Task(
                                        project_id=project.id,
                                        name=card.get("name"),
                                        description=card.get("desc", ""),
                                        status=self._map_trello_list_to_status(card.get("idList"))
                                    )
                                    db.session.add(task)
                                    db.session.flush()

                                # Store Trello card ID in metadata
                                if not hasattr(task, 'metadata') or not task.metadata:
                                    task.metadata = {}
                                task.metadata['trello_card_id'] = card.get("id")

                        synced_count += 1
                    except Exception as e:
                        errors.append(f"Error syncing board {board.get('name')}: {str(e)}")

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

    def _map_trello_list_to_status(self, list_id: str) -> str:
        """Map Trello list to task status."""
        from app.models import Settings
        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("trello")
        api_key = creds.get("api_key") or os.getenv("TRELLO_API_KEY")
        token = self.get_access_token()
        
        if not token or not api_key:
            return "todo"
        
        try:
            # Fetch list name
            list_response = requests.get(
                f"{self.BASE_URL}/lists/{list_id}",
                params={"key": api_key, "token": token}
            )
            
            if list_response.status_code == 200:
                list_data = list_response.json()
                list_name = list_data.get("name", "").lower()
                
                # Map common list names to statuses
                if "done" in list_name or "completed" in list_name or "closed" in list_name:
                    return "completed"
                elif "in progress" in list_name or "doing" in list_name or "active" in list_name:
                    return "in_progress"
                elif "todo" in list_name or "to do" in list_name or "backlog" in list_name:
                    return "todo"
        except Exception:
            pass
        
        return "todo"

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "board_ids",
                    "type": "array",
                    "label": "Board IDs",
                    "description": "Trello board IDs to sync (leave empty to sync all)"
                },
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "trello_to_timetracker", "label": "Trello → TimeTracker"},
                        {"value": "timetracker_to_trello", "label": "TimeTracker → Trello"},
                        {"value": "bidirectional", "label": "Bidirectional"}
                    ],
                    "default": "trello_to_timetracker"
                }
            ],
            "required": []
        }

