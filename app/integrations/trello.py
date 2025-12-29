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
            "redirect_uri": redirect_uri,
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
            response = requests.get(f"{self.BASE_URL}/members/me", params={"key": api_key, "token": token})
            if response.status_code == 200:
                user_data = response.json()
                user_info = {
                    "id": user_data.get("id"),
                    "username": user_data.get("username"),
                    "fullName": user_data.get("fullName"),
                    "email": user_data.get("email"),
                }
        except Exception:
            pass

        return {
            "access_token": token,
            "refresh_token": None,  # Trello tokens don't expire
            "expires_at": None,
            "token_type": "Bearer",
            "extra_data": user_info,
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token (Trello tokens don't expire)."""
        # Trello tokens don't expire, so just return current token
        return {"access_token": self.credentials.access_token if self.credentials else None, "expires_at": None}

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Trello."""
        try:
            from app.models import Settings

            settings = Settings.get_settings()
            creds = settings.get_integration_credentials("trello")
            api_key = creds.get("api_key") or os.getenv("TRELLO_API_KEY")

            headers = {"Authorization": f"Bearer {self.get_access_token()}"}
            response = requests.get(
                f"{self.BASE_URL}/members/me", params={"key": api_key, "token": self.get_access_token()}
            )

            if response.status_code == 200:
                user_data = response.json()
                return {"success": True, "message": f"Connected to Trello as {user_data.get('fullName', 'Unknown')}"}
            else:
                return {"success": False, "message": f"Connection test failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {str(e)}"}

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

            # Get sync direction from config
            sync_direction = self.integration.config.get("sync_direction", "trello_to_timetracker") if self.integration else "trello_to_timetracker"
            
            if sync_direction in ("trello_to_timetracker", "bidirectional"):
                trello_result = self._sync_trello_to_timetracker(api_key, token)
                # If bidirectional, also sync TimeTracker to Trello
                if sync_direction == "bidirectional":
                    tracker_result = self._sync_timetracker_to_trello(api_key, token)
                    # Merge results
                    if trello_result.get("success") and tracker_result.get("success"):
                        return {
                            "success": True,
                            "synced_count": trello_result.get("synced_count", 0) + tracker_result.get("synced_count", 0),
                            "errors": trello_result.get("errors", []) + tracker_result.get("errors", []),
                            "message": f"Bidirectional sync: Trello→TimeTracker: {trello_result.get('synced_count', 0)} items | TimeTracker→Trello: {tracker_result.get('synced_count', 0)} items",
                        }
                    elif trello_result.get("success"):
                        return trello_result
                    elif tracker_result.get("success"):
                        return tracker_result
                    else:
                        return {"success": False, "message": f"Both sync directions failed. Trello→TimeTracker: {trello_result.get('message')}, TimeTracker→Trello: {tracker_result.get('message')}"}
                return trello_result
            
            # Handle TimeTracker to Trello sync
            if sync_direction == "timetracker_to_trello":
                return self._sync_timetracker_to_trello(api_key, token)
            
            return {"success": False, "message": f"Unknown sync direction: {sync_direction}"}

        except Exception as e:
            return {"success": False, "message": f"Sync failed: {str(e)}"}
    
    def _sync_trello_to_timetracker(self, api_key: str, token: str) -> Dict[str, Any]:
        """Sync Trello boards and cards to TimeTracker projects and tasks."""
        from app.models import Project, Task
        from app import db

        synced_count = 0
        errors = []

        # Get boards
        boards_response = requests.get(
            f"{self.BASE_URL}/members/me/boards", params={"key": api_key, "token": token, "filter": "open"}
        )

        if boards_response.status_code == 200:
            boards = boards_response.json()
            
            # Filter by board_ids if configured
            board_ids = self.integration.config.get("board_ids", []) if self.integration else []
            if board_ids:
                boards = [b for b in boards if b.get("id") in board_ids]

            for board in boards:
                try:
                    # Create or update project from board
                    project = Project.query.filter_by(
                        user_id=self.integration.user_id, name=board.get("name")
                    ).first()

                    if not project:
                        project = Project(
                            name=board.get("name"),
                            description=board.get("desc", ""),
                            user_id=self.integration.user_id,
                            status="active",
                        )
                        db.session.add(project)
                        db.session.flush()

                    # Store Trello board ID in metadata
                    if not hasattr(project, "metadata") or not project.metadata:
                        project.metadata = {}
                    project.metadata["trello_board_id"] = board.get("id")

                    # Sync cards as tasks
                    cards_response = requests.get(
                        f"{self.BASE_URL}/boards/{board.get('id')}/cards",
                        params={"key": api_key, "token": token, "filter": "open"},
                    )

                    if cards_response.status_code == 200:
                        cards = cards_response.json()

                        for card in cards:
                            # Find or create task
                            task = Task.query.filter_by(project_id=project.id, name=card.get("name")).first()

                            if not task:
                                task = Task(
                                    project_id=project.id,
                                    name=card.get("name"),
                                    description=card.get("desc", ""),
                                    status=self._map_trello_list_to_status(card.get("idList")),
                                )
                                db.session.add(task)
                                db.session.flush()
                            else:
                                # Update existing task if needed
                                if card.get("desc") and task.description != card.get("desc"):
                                    task.description = card.get("desc")
                                # Update status based on list
                                new_status = self._map_trello_list_to_status(card.get("idList"))
                                if task.status != new_status:
                                    task.status = new_status

                            # Store Trello card ID in metadata
                            if not hasattr(task, "metadata") or not task.metadata:
                                task.metadata = {}
                            task.metadata["trello_card_id"] = card.get("id")
                            task.metadata["trello_list_id"] = card.get("idList")

                    synced_count += 1
                except Exception as e:
                    errors.append(f"Error syncing board {board.get('name')}: {str(e)}")

        db.session.commit()

        return {"success": True, "synced_count": synced_count, "errors": errors}
    
    def _sync_timetracker_to_trello(self, api_key: str, token: str) -> Dict[str, Any]:
        """Sync TimeTracker tasks to Trello cards."""
        from app.models import Project, Task
        from app import db

        synced_count = 0
        errors = []

        # Get all projects that have Trello board IDs
        projects = Project.query.filter_by(user_id=self.integration.user_id, status="active").all()
        
        for project in projects:
            # Check if project has Trello board ID
            trello_board_id = None
            if hasattr(project, "metadata") and project.metadata:
                trello_board_id = project.metadata.get("trello_board_id")
            
            if not trello_board_id:
                # Try to find or create board
                board_name = project.name
                boards_response = requests.get(
                    f"{self.BASE_URL}/members/me/boards",
                    params={"key": api_key, "token": token, "filter": "open"}
                )
                
                if boards_response.status_code == 200:
                    boards = boards_response.json()
                    matching_board = next((b for b in boards if b.get("name") == board_name), None)
                    
                    if matching_board:
                        trello_board_id = matching_board.get("id")
                    else:
                        # Create new board (optional - might require additional permissions)
                        try:
                            create_response = requests.post(
                                f"{self.BASE_URL}/boards",
                                params={"key": api_key, "token": token, "name": board_name}
                            )
                            if create_response.status_code == 200:
                                trello_board_id = create_response.json().get("id")
                        except Exception as e:
                            errors.append(f"Could not create Trello board for project {project.name}: {str(e)}")
                            continue
                
                if trello_board_id:
                    if not hasattr(project, "metadata") or not project.metadata:
                        project.metadata = {}
                    project.metadata["trello_board_id"] = trello_board_id
            
            if not trello_board_id:
                continue
            
            # Get lists for this board
            lists_response = requests.get(
                f"{self.BASE_URL}/boards/{trello_board_id}/lists",
                params={"key": api_key, "token": token, "filter": "open"}
            )
            
            if lists_response.status_code != 200:
                errors.append(f"Could not get lists for board {project.name}")
                continue
            
            lists = lists_response.json()
            # Create a mapping of status to list ID
            status_to_list = {}
            for lst in lists:
                list_name = lst.get("name", "").lower()
                if "todo" in list_name or "to do" in list_name or "backlog" in list_name:
                    status_to_list["todo"] = lst.get("id")
                elif "in progress" in list_name or "doing" in list_name or "active" in list_name:
                    status_to_list["in_progress"] = lst.get("id")
                elif "done" in list_name or "completed" in list_name:
                    status_to_list["done"] = lst.get("id")
                elif "review" in list_name:
                    status_to_list["review"] = lst.get("id")
            
            # Default to first list if no mapping found
            default_list_id = lists[0].get("id") if lists else None
            
            # Get tasks for this project
            tasks = Task.query.filter_by(project_id=project.id).all()
            
            for task in tasks:
                try:
                    # Check if task already has Trello card ID
                    trello_card_id = None
                    if hasattr(task, "metadata") and task.metadata:
                        trello_card_id = task.metadata.get("trello_card_id")
                    
                    # Determine target list
                    target_list_id = status_to_list.get(task.status, default_list_id)
                    if not target_list_id:
                        continue
                    
                    if trello_card_id:
                        # Update existing card
                        update_data = {
                            "name": task.name,
                            "desc": task.description or "",
                            "idList": target_list_id,
                        }
                        update_response = requests.put(
                            f"{self.BASE_URL}/cards/{trello_card_id}",
                            params={"key": api_key, "token": token},
                            json=update_data
                        )
                        if update_response.status_code == 200:
                            synced_count += 1
                        else:
                            errors.append(f"Failed to update Trello card for task {task.id}: {update_response.status_code}")
                    else:
                        # Create new card
                        create_data = {
                            "name": task.name,
                            "desc": task.description or "",
                            "idList": target_list_id,
                        }
                        create_response = requests.post(
                            f"{self.BASE_URL}/cards",
                            params={"key": api_key, "token": token},
                            json=create_data
                        )
                        if create_response.status_code == 200:
                            card_data = create_response.json()
                            trello_card_id = card_data.get("id")
                            
                            # Store Trello card ID in task metadata
                            if not hasattr(task, "metadata") or not task.metadata:
                                task.metadata = {}
                            task.metadata["trello_card_id"] = trello_card_id
                            task.metadata["trello_list_id"] = target_list_id
                            
                            synced_count += 1
                        else:
                            errors.append(f"Failed to create Trello card for task {task.id}: {create_response.status_code}")
                            
                except Exception as e:
                    errors.append(f"Error syncing task {task.id} to Trello: {str(e)}")
        
        db.session.commit()
        
        return {"success": True, "synced_count": synced_count, "errors": errors}

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
            list_response = requests.get(f"{self.BASE_URL}/lists/{list_id}", params={"key": api_key, "token": token})

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
                    "type": "text",
                    "label": "Board IDs",
                    "required": False,
                    "placeholder": "board-id-1, board-id-2",
                    "description": "Comma-separated list of Trello board IDs to sync (leave empty to sync all)",
                    "help": "Find board IDs in Trello board URLs or API. Leave empty to sync all accessible boards.",
                },
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "trello_to_timetracker", "label": "Trello → TimeTracker (Import only)"},
                        {"value": "timetracker_to_trello", "label": "TimeTracker → Trello (Export only)"},
                        {"value": "bidirectional", "label": "Bidirectional (Two-way sync)"},
                    ],
                    "default": "trello_to_timetracker",
                    "description": "Choose how data flows between Trello and TimeTracker",
                },
                {
                    "name": "sync_items",
                    "type": "array",
                    "label": "Items to Sync",
                    "options": [
                        {"value": "boards", "label": "Boards (Projects)"},
                        {"value": "cards", "label": "Cards (Tasks)"},
                        {"value": "lists", "label": "Lists"},
                    ],
                    "default": ["boards", "cards"],
                    "description": "Select which items to synchronize",
                },
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": False,
                    "description": "Automatically sync when webhooks are received from Trello",
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
                    "name": "list_status_mapping",
                    "type": "json",
                    "label": "List to Status Mapping",
                    "placeholder": '{"To Do": "todo", "In Progress": "in_progress", "Done": "completed"}',
                    "description": "Map Trello list names to TimeTracker task statuses (JSON format)",
                    "help": "Customize how Trello list names map to TimeTracker task statuses",
                },
                {
                    "name": "sync_archived",
                    "type": "boolean",
                    "label": "Sync Archived Items",
                    "default": False,
                    "description": "Include archived boards and cards in sync",
                },
            ],
            "required": [],
            "sections": [
                {
                    "title": "Board Settings",
                    "description": "Configure which Trello boards to sync",
                    "fields": ["board_ids", "sync_archived"],
                },
                {
                    "title": "Sync Settings",
                    "description": "Configure what and how to sync",
                    "fields": ["sync_direction", "sync_items", "auto_sync", "sync_interval"],
                },
                {
                    "title": "Data Mapping",
                    "description": "Customize how data translates between Trello and TimeTracker",
                    "fields": ["list_status_mapping"],
                },
            ],
            "sync_settings": {
                "enabled": True,
                "auto_sync": False,
                "sync_interval": "manual",
                "sync_direction": "trello_to_timetracker",
                "sync_items": ["boards", "cards"],
            },
        }
