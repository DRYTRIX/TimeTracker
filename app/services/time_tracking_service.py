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
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        start_time: datetime = None,
        end_time: datetime = None,
        task_id: Optional[int] = None,
        notes: Optional[str] = None,
        tags: Optional[str] = None,
        billable: bool = True,
        paid: bool = False,
        invoice_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a manual time entry.

        Returns:
            dict with 'success', 'message', and 'entry' keys
        """
        # Validate that either project_id or client_id is provided
        if not project_id and not client_id:
            return {
                "success": False,
                "message": "Either project or client must be selected",
                "error": "missing_project_or_client",
            }

        # Validate project if provided
        if project_id:
            project = self.project_repo.get_by_id(project_id)
            if not project:
                return {"success": False, "message": "Invalid project", "error": "invalid_project"}

            # Validate task if provided (only valid when project_id is set)
            if task_id:
                task = Task.query.filter_by(id=task_id, project_id=project_id).first()
                if not task:
                    return {"success": False, "message": "Invalid task for selected project", "error": "invalid_task"}

        # Validate client if provided
        if client_id:
            from app.repositories import ClientRepository

            client_repo = ClientRepository()
            client = client_repo.get_by_id(client_id)
            if not client:
                return {"success": False, "message": "Invalid client", "error": "invalid_client"}

            # Task cannot be set when billing directly to client
            if task_id:
                return {
                    "success": False,
                    "message": "Tasks can only be assigned to project-based time entries",
                    "error": "task_not_allowed",
                }

        # Validate time range
        if end_time <= start_time:
            return {"success": False, "message": "End time must be after start time", "error": "invalid_time_range"}

        # Create entry
        entry = self.time_entry_repo.create_manual_entry(
            user_id=user_id,
            project_id=project_id,
            client_id=client_id,
            start_time=start_time,
            end_time=end_time,
            task_id=task_id,
            notes=notes,
            tags=tags,
            billable=billable,
            paid=paid,
            invoice_number=invoice_number,
        )

        commit_data = {"user_id": user_id}
        if project_id:
            commit_data["project_id"] = project_id
        if client_id:
            commit_data["client_id"] = client_id

        if not safe_commit("create_manual_entry", commit_data):
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
        client_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[TimeEntry]:
        """Get time entries for a user with optional filters"""
        if start_date and end_date:
            return self.time_entry_repo.get_by_date_range(
                start_date=start_date,
                end_date=end_date,
                user_id=user_id,
                project_id=project_id,
                client_id=client_id,
                include_relations=True,
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

    def update_entry(
        self,
        entry_id: int,
        user_id: int,
        is_admin: bool = False,
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        task_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        notes: Optional[str] = None,
        tags: Optional[str] = None,
        billable: Optional[bool] = None,
        paid: Optional[bool] = None,
        invoice_number: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update a time entry.

        Args:
            entry_id: ID of the time entry to update
            user_id: ID of the user performing the update
            is_admin: Whether the user is an admin
            project_id: Optional new project ID
            client_id: Optional new client ID
            task_id: Optional new task ID
            start_time: Optional new start time
            end_time: Optional new end time
            notes: Optional new notes
            tags: Optional new tags
            billable: Optional new billable status
            paid: Optional new paid status
            invoice_number: Optional new invoice number
            reason: Optional reason for the change

        Returns:
            dict with 'success', 'message', and 'entry' keys
        """
        entry = self.time_entry_repo.get_by_id(entry_id)

        if not entry:
            return {"success": False, "message": "Time entry not found", "error": "not_found"}

        # Check permissions
        if not is_admin and entry.user_id != user_id:
            return {"success": False, "message": "Access denied", "error": "access_denied"}

        # Don't allow updating active entries to have end_time
        if entry.is_active and end_time is not None:
            return {
                "success": False,
                "message": "Cannot set end_time on active timer. Stop the timer first.",
                "error": "timer_active",
            }

        # Capture old state before changes
        from app.utils.audit import capture_timeentry_state, capture_timeentry_metadata
        full_old_state = capture_timeentry_state(entry)
        entity_metadata = capture_timeentry_metadata(entry)

        # Update fields
        if project_id is not None:
            # Validate project
            project = self.project_repo.get_by_id(project_id)
            if not project:
                return {"success": False, "message": "Invalid project", "error": "invalid_project"}
            entry.project_id = project_id
            # Clear client_id when setting project_id
            entry.client_id = None

        # Handle client_id update
        if client_id is not None:
            from app.repositories import ClientRepository

            client_repo = ClientRepository()
            client = client_repo.get_by_id(client_id)
            if not client:
                return {"success": False, "message": "Invalid client", "error": "invalid_client"}
            entry.client_id = client_id
            # Clear project_id and task_id when setting client_id
            entry.project_id = None
            entry.task_id = None

        if task_id is not None:
            # Task can only be set when project_id is set
            if not entry.project_id:
                return {
                    "success": False,
                    "message": "Task can only be assigned to project-based time entries",
                    "error": "task_requires_project",
                }
            entry.task_id = task_id
        if start_time is not None:
            entry.start_time = start_time
        if end_time is not None:
            entry.end_time = end_time
        # Recompute stored duration when start or end time changed
        if entry.end_time and (start_time is not None or end_time is not None):
            entry.calculate_duration()
        if notes is not None:
            entry.notes = notes
        if tags is not None:
            entry.tags = tags
        if billable is not None:
            entry.billable = billable
        if paid is not None:
            entry.paid = paid
            # Clear invoice number if marking as unpaid
            if not entry.paid:
                entry.invoice_number = None
        if invoice_number is not None:
            entry.invoice_number = invoice_number.strip() if invoice_number else None

        entry.updated_at = local_now()

        if not safe_commit("update_entry", {"user_id": user_id, "entry_id": entry_id}):
            return {
                "success": False,
                "message": "Could not update time entry due to a database error",
                "error": "database_error",
            }

        # Capture new state after changes and create comprehensive audit log
        try:
            # Refresh entry to get updated values
            db.session.refresh(entry)
            full_new_state = capture_timeentry_state(entry)
            updated_metadata = capture_timeentry_metadata(entry)
            
            from app.models.audit_log import AuditLog
            from app.utils.audit import get_request_info
            ip_address, user_agent, request_path = get_request_info()
            
            entity_name = entry.project.name if entry.project else (entry.client.name if entry.client else "Unknown")
            
            AuditLog.log_change(
                user_id=user_id,
                action="updated",
                entity_type="TimeEntry",
                entity_id=entry_id,
                entity_name=entity_name,
                change_description=f"Updated time entry for {entity_name}",
                reason=reason,
                entity_metadata=updated_metadata,
                full_old_state=full_old_state,
                full_new_state=full_new_state,
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request_path,
            )
            db.session.commit()
        except Exception as e:
            # Don't fail update if audit logging fails
            import logging
            logging.getLogger(__name__).warning(f"Failed to create audit log for TimeEntry update: {e}")

        return {"success": True, "message": "Time entry updated successfully", "entry": entry}

    def delete_entry(self, user_id: int, entry_id: int, is_admin: bool = False, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete a time entry.

        Args:
            user_id: ID of the user performing the deletion
            entry_id: ID of the time entry to delete
            is_admin: Whether the user is an admin
            reason: Optional reason for deletion

        Returns:
            dict with 'success' and 'message' keys
        """
        entry = self.time_entry_repo.get_by_id(entry_id)

        if not entry:
            return {"success": False, "message": "Time entry not found", "error": "not_found"}

        # Check permissions
        if not is_admin and entry.user_id != user_id:
            return {"success": False, "message": "Access denied", "error": "access_denied"}

        # Don't allow deletion of active entries
        if entry.is_active:
            return {
                "success": False,
                "message": "Cannot delete active time entry. Stop the timer first.",
                "error": "timer_active",
            }

        # Capture entry info for logging before deletion
        project_name = entry.project.name if entry.project else None
        client_name = entry.client.name if entry.client else None
        entity_name = project_name or client_name or "Unknown"
        duration_formatted = entry.duration_formatted

        # Capture full state and metadata for audit logging
        from app.utils.audit import capture_timeentry_state, capture_timeentry_metadata, get_request_info
        from app.models.audit_log import AuditLog
        
        full_old_state = capture_timeentry_state(entry)
        entity_metadata = capture_timeentry_metadata(entry)
        ip_address, user_agent, request_path = get_request_info()

        if self.time_entry_repo.delete(entry):
            if safe_commit("delete_entry", {"user_id": user_id, "entry_id": entry_id}):
                # Create comprehensive audit log entry
                try:
                    AuditLog.log_change(
                        user_id=user_id,
                        action="deleted",
                        entity_type="TimeEntry",
                        entity_id=entry_id,
                        entity_name=entity_name,
                        change_description=f"Deleted time entry for {entity_name} - {duration_formatted}",
                        reason=reason,
                        entity_metadata=entity_metadata,
                        full_old_state=full_old_state,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_path=request_path,
                    )
                    db.session.commit()
                except Exception as e:
                    # Don't fail deletion if audit logging fails
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to create audit log for TimeEntry deletion: {e}")

                # Log activity
                from app.models import Activity
                from flask import request
                Activity.log(
                    user_id=user_id,
                    action="deleted",
                    entity_type="time_entry",
                    entity_id=entry_id,
                    entity_name=entity_name,
                    description=f'Deleted time entry for {entity_name} - {duration_formatted}',
                    extra_data={"project_name": project_name, "client_name": client_name, "duration_formatted": duration_formatted, "reason": reason},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                return {"success": True, "message": "Time entry deleted successfully"}

        return {"success": False, "message": "Could not delete time entry", "error": "database_error"}
