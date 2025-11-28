"""
Service for time tracking business logic.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from flask_login import current_user
from app import db
from app.repositories import TimeEntryRepository, ProjectRepository
from app.models import TimeEntry, Project, Task
from app.constants import TimeEntrySource, TimeEntryStatus
from app.utils.timezone import local_now, parse_local_datetime
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent


class TimeTrackingService:
    """Service for time tracking operations"""

    def __init__(self):
        self.time_entry_repo = TimeEntryRepository()
        self.project_repo = ProjectRepository()

    def start_timer(
        self,
        user_id: int,
        project_id: int,
        task_id: Optional[int] = None,
        notes: Optional[str] = None,
        template_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Start a new timer for a user.

        Returns:
            dict with 'success', 'message', and 'timer' keys
        """
        # Load template if provided
        if template_id:
            from app.models import TimeEntryTemplate

            template = TimeEntryTemplate.query.filter_by(id=template_id, user_id=user_id).first()
            if template:
                # Override with template values if not explicitly set
                if not project_id and template.project_id:
                    project_id = template.project_id
                if not task_id and template.task_id:
                    task_id = template.task_id
                if not notes and template.default_notes:
                    notes = template.default_notes
                # Mark template as used
                template.record_usage()
                db.session.commit()
        """
        Start a new timer for a user.
        
        Returns:
            dict with 'success', 'message', and 'timer' keys
        """
        # Check if user already has an active timer
        active_timer = self.time_entry_repo.get_active_timer(user_id)
        if active_timer:
            return {
                "success": False,
                "message": "You already have an active timer. Stop it before starting a new one.",
                "error": "timer_already_running",
            }

        # Validate project
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return {"success": False, "message": "Invalid project selected", "error": "invalid_project"}

        # Check project status
        if project.status == "archived":
            return {
                "success": False,
                "message": "Cannot start timer for an archived project. Please unarchive the project first.",
                "error": "project_archived",
            }

        if project.status != "active":
            return {
                "success": False,
                "message": "Cannot start timer for an inactive project",
                "error": "project_inactive",
            }

        # Load template if provided
        if template_id:
            from app.models import TimeEntryTemplate

            template = TimeEntryTemplate.query.filter_by(id=template_id, user_id=user_id).first()
            if template:
                if not project_id and template.project_id:
                    project_id = template.project_id
                if not task_id and template.task_id:
                    task_id = template.task_id
                if not notes and template.default_notes:
                    notes = template.default_notes
                template.record_usage()

        # Validate task if provided
        if task_id:
            task = Task.query.filter_by(id=task_id, project_id=project_id).first()
            if not task:
                return {
                    "success": False,
                    "message": "Selected task is invalid for the chosen project",
                    "error": "invalid_task",
                }

        # Create timer
        timer = self.time_entry_repo.create_timer(
            user_id=user_id, project_id=project_id, task_id=task_id, notes=notes, source=TimeEntrySource.AUTO.value
        )

        if not safe_commit("start_timer", {"user_id": user_id, "project_id": project_id}):
            return {
                "success": False,
                "message": "Could not start timer due to a database error",
                "error": "database_error",
            }

        # Emit domain event
        emit_event(
            WebhookEvent.TIME_ENTRY_CREATED.value, {"entry_id": timer.id, "user_id": user_id, "project_id": project_id}
        )

        return {"success": True, "message": "Timer started successfully", "timer": timer}

    def stop_timer(self, user_id: int, entry_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Stop the active timer for a user.

        Returns:
            dict with 'success', 'message', and 'entry' keys
        """
        if entry_id:
            entry = self.time_entry_repo.get_by_id(entry_id)
        else:
            entry = self.time_entry_repo.get_active_timer(user_id)

        if not entry:
            return {"success": False, "message": "No active timer found", "error": "no_active_timer"}

        if entry.user_id != user_id:
            return {"success": False, "message": "You can only stop your own timer", "error": "unauthorized"}

        if entry.end_time is not None:
            return {"success": False, "message": "Timer is already stopped", "error": "timer_already_stopped"}

        # Stop the timer
        entry.end_time = local_now()
        entry.calculate_duration()

        if not safe_commit("stop_timer", {"user_id": user_id, "entry_id": entry.id}):
            return {
                "success": False,
                "message": "Could not stop timer due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Timer stopped successfully", "entry": entry}

    def create_manual_entry(
        self,
        user_id: int,
        project_id: int,
        start_time: datetime,
        end_time: datetime,
        task_id: Optional[int] = None,
        notes: Optional[str] = None,
        tags: Optional[str] = None,
        billable: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a manual time entry.

        Returns:
            dict with 'success', 'message', and 'entry' keys
        """
        # Validate project
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return {"success": False, "message": "Invalid project", "error": "invalid_project"}

        # Validate time range
        if end_time <= start_time:
            return {"success": False, "message": "End time must be after start time", "error": "invalid_time_range"}

        # Validate task if provided
        if task_id:
            task = Task.query.filter_by(id=task_id, project_id=project_id).first()
            if not task:
                return {"success": False, "message": "Invalid task for selected project", "error": "invalid_task"}

        # Create entry
        entry = self.time_entry_repo.create_manual_entry(
            user_id=user_id,
            project_id=project_id,
            start_time=start_time,
            end_time=end_time,
            task_id=task_id,
            notes=notes,
            tags=tags,
            billable=billable,
        )

        if not safe_commit("create_manual_entry", {"user_id": user_id, "project_id": project_id}):
            return {
                "success": False,
                "message": "Could not create time entry due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Time entry created successfully", "entry": entry}

    def get_user_entries(
        self,
        user_id: int,
        limit: Optional[int] = None,
        offset: int = 0,
        project_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[TimeEntry]:
        """Get time entries for a user with optional filters"""
        if start_date and end_date:
            return self.time_entry_repo.get_by_date_range(
                start_date=start_date, end_date=end_date, user_id=user_id, project_id=project_id, include_relations=True
            )
        elif project_id:
            return self.time_entry_repo.get_by_project(
                project_id=project_id, limit=limit, offset=offset, include_relations=True
            )
        else:
            return self.time_entry_repo.get_by_user(user_id=user_id, limit=limit, offset=offset, include_relations=True)

    def get_active_timer(self, user_id: int) -> Optional[TimeEntry]:
        """Get the active timer for a user"""
        return self.time_entry_repo.get_active_timer(user_id)

    def delete_entry(self, user_id: int, entry_id: int) -> Dict[str, Any]:
        """
        Delete a time entry.

        Returns:
            dict with 'success' and 'message' keys
        """
        entry = self.time_entry_repo.get_by_id(entry_id)

        if not entry:
            return {"success": False, "message": "Time entry not found", "error": "not_found"}

        # Check permissions (user can only delete their own entries unless admin)
        from flask_login import current_user

        if entry.user_id != user_id and not (hasattr(current_user, "is_admin") and current_user.is_admin):
            return {
                "success": False,
                "message": "You do not have permission to delete this entry",
                "error": "unauthorized",
            }

        if self.time_entry_repo.delete(entry):
            if safe_commit("delete_entry", {"user_id": user_id, "entry_id": entry_id}):
                return {"success": True, "message": "Time entry deleted successfully"}

        return {"success": False, "message": "Could not delete time entry", "error": "database_error"}
