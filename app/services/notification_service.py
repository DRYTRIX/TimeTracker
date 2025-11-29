"""
Service for notifications and event handling.
"""

from typing import Dict, Any, Optional
from flask import current_app
from app.utils.webhook_dispatcher import dispatch_webhook
from app.constants import WebhookEvent, NotificationType


class NotificationService:
    """Service for notifications and events"""

    def notify_time_entry_created(self, entry_id: int, user_id: int, project_id: int) -> None:
        """Notify that a time entry was created"""
        try:
            dispatch_webhook(
                event=WebhookEvent.TIME_ENTRY_CREATED.value,
                data={"entry_id": entry_id, "user_id": user_id, "project_id": project_id},
            )
        except Exception as e:
            current_app.logger.error(f"Failed to dispatch time entry created webhook: {e}")

    def notify_time_entry_updated(self, entry_id: int, user_id: int, project_id: int) -> None:
        """Notify that a time entry was updated"""
        try:
            dispatch_webhook(
                event=WebhookEvent.TIME_ENTRY_UPDATED.value,
                data={"entry_id": entry_id, "user_id": user_id, "project_id": project_id},
            )
        except Exception as e:
            current_app.logger.error(f"Failed to dispatch time entry updated webhook: {e}")

    def notify_project_created(self, project_id: int, client_id: int) -> None:
        """Notify that a project was created"""
        try:
            dispatch_webhook(
                event=WebhookEvent.PROJECT_CREATED.value, data={"project_id": project_id, "client_id": client_id}
            )
        except Exception as e:
            current_app.logger.error(f"Failed to dispatch project created webhook: {e}")

    def notify_invoice_created(self, invoice_id: int, project_id: int, client_id: int) -> None:
        """Notify that an invoice was created"""
        try:
            dispatch_webhook(
                event=WebhookEvent.INVOICE_CREATED.value,
                data={"invoice_id": invoice_id, "project_id": project_id, "client_id": client_id},
            )
        except Exception as e:
            current_app.logger.error(f"Failed to dispatch invoice created webhook: {e}")
