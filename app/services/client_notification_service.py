"""
Client Notification Service
Handles notifications for client portal users
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from app import db
from app.models.client_notification import ClientNotification, ClientNotificationPreferences, NotificationType
from app.models import Client, Contact
from app.utils.email import send_email
import logging

logger = logging.getLogger(__name__)


class ClientNotificationService:
    """Service for managing client notifications"""

    def create_notification(
        self,
        client_id: int,
        notification_type: str,
        title: str,
        message: str,
        link_url: Optional[str] = None,
        link_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        send_email: bool = True,
    ) -> ClientNotification:
        """Create a notification for a client"""
        notification = ClientNotification(
            client_id=client_id,
            type=notification_type,
            title=title,
            message=message,
            link_url=link_url,
            link_text=link_text,
            extra_data=metadata or {},
        )
        db.session.add(notification)
        db.session.commit()

        # Send email if enabled
        if send_email:
            try:
                self._send_email_notification(notification)
            except Exception as e:
                logger.error(f"Failed to send email notification: {e}", exc_info=True)

        return notification

    def notify_invoice_created(self, invoice_id: int, client_id: int):
        """Notify client about new invoice"""
        from app.models import Invoice

        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return

        notification = self.create_notification(
            client_id=client_id,
            notification_type=NotificationType.INVOICE_CREATED.value,
            title=f"New Invoice: {invoice.invoice_number}",
            message=f"A new invoice has been created for {invoice.total_amount} {invoice.currency_code}.",
            link_url=f"/client-portal/invoices/{invoice_id}",
            link_text="View Invoice",
            metadata={"invoice_id": invoice_id},
        )
        return notification

    def notify_invoice_paid(self, invoice_id: int, client_id: int, amount: float):
        """Notify client about invoice payment"""
        from app.models import Invoice

        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return

        notification = self.create_notification(
            client_id=client_id,
            notification_type=NotificationType.INVOICE_PAID.value,
            title=f"Invoice Paid: {invoice.invoice_number}",
            message=f"Payment of {amount} {invoice.currency_code} has been received for invoice {invoice.invoice_number}.",
            link_url=f"/client-portal/invoices/{invoice_id}",
            link_text="View Invoice",
            metadata={"invoice_id": invoice_id, "amount": amount},
        )
        return notification

    def notify_invoice_overdue(self, invoice_id: int, client_id: int, days_overdue: int):
        """Notify client about overdue invoice"""
        from app.models import Invoice

        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return

        notification = self.create_notification(
            client_id=client_id,
            notification_type=NotificationType.INVOICE_OVERDUE.value,
            title=f"Overdue Invoice: {invoice.invoice_number}",
            message=f"Invoice {invoice.invoice_number} is {days_overdue} days overdue. Amount: {invoice.outstanding_amount} {invoice.currency_code}.",
            link_url=f"/client-portal/invoices/{invoice_id}",
            link_text="View Invoice",
            metadata={"invoice_id": invoice_id, "days_overdue": days_overdue},
        )
        return notification

    def notify_time_entry_approval(self, approval_id: int, client_id: int):
        """Notify client about time entry approval request"""
        from app.models.client_time_approval import ClientTimeApproval

        approval = ClientTimeApproval.query.get(approval_id)
        if not approval or not approval.time_entry:
            return

        notification = self.create_notification(
            client_id=client_id,
            notification_type=NotificationType.TIME_ENTRY_APPROVAL.value,
            title="Time Entry Approval Requested",
            message=f"A time entry for {approval.time_entry.project.name if approval.time_entry.project else 'project'} requires your approval.",
            link_url=f"/client-portal/approvals/{approval_id}",
            link_text="Review Approval",
            metadata={"approval_id": approval_id, "time_entry_id": approval.time_entry_id},
        )
        return notification

    def notify_quote_available(self, quote_id: int, client_id: int):
        """Notify client about new quote"""
        from app.models import Quote

        quote = Quote.query.get(quote_id)
        if not quote:
            return

        notification = self.create_notification(
            client_id=client_id,
            notification_type=NotificationType.QUOTE_AVAILABLE.value,
            title=f"New Quote: {quote.quote_number}",
            message=f"A new quote has been created for {quote.total_amount} {quote.currency_code}.",
            link_url=f"/client-portal/quotes/{quote_id}",
            link_text="View Quote",
            metadata={"quote_id": quote_id},
        )
        return notification

    def notify_project_milestone(self, project_id: int, client_id: int, milestone_name: str):
        """Notify client about project milestone"""
        from app.models import Project

        project = Project.query.get(project_id)
        if not project:
            return

        notification = self.create_notification(
            client_id=client_id,
            notification_type=NotificationType.PROJECT_MILESTONE.value,
            title=f"Milestone Reached: {milestone_name}",
            message=f"Project {project.name} has reached the milestone: {milestone_name}.",
            link_url=f"/client-portal/projects",
            link_text="View Projects",
            metadata={"project_id": project_id, "milestone": milestone_name},
        )
        return notification

    def notify_budget_alert(self, project_id: int, client_id: int, budget_percentage: float):
        """Notify client about budget threshold"""
        from app.models import Project

        project = Project.query.get(project_id)
        if not project:
            return

        notification = self.create_notification(
            client_id=client_id,
            notification_type=NotificationType.BUDGET_ALERT.value,
            title=f"Budget Alert: {project.name}",
            message=f"Project {project.name} has reached {budget_percentage:.0f}% of its budget.",
            link_url=f"/client-portal/projects",
            link_text="View Project",
            metadata={"project_id": project_id, "budget_percentage": budget_percentage},
        )
        return notification

    def _send_email_notification(self, notification: ClientNotification):
        """Send email notification to client contacts"""
        # Get notification preferences
        prefs = ClientNotificationPreferences.query.filter_by(client_id=notification.client_id).first()
        if not prefs or not prefs.email_enabled:
            return

        # Check if email is enabled for this notification type
        try:
            notif_type = NotificationType(notification.type)
            if not prefs.should_send_email(notif_type):
                return
        except ValueError:
            # Unknown notification type, default to sending
            pass

        # Get client contacts
        contacts = Contact.query.filter_by(client_id=notification.client_id, is_active=True).all()
        if not contacts:
            return

        # Send email to all active contacts
        for contact in contacts:
            if contact.email:
                try:
                    send_email(
                        to=contact.email,
                        subject=notification.title,
                        template="email/client_notification.html",
                        notification=notification,
                        contact=contact,
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification email to {contact.email}: {e}", exc_info=True)

    def mark_as_read(self, notification_id: int, client_id: int) -> bool:
        """Mark a notification as read"""
        notification = ClientNotification.query.filter_by(id=notification_id, client_id=client_id).first()
        if not notification:
            return False

        notification.mark_as_read()
        return True

    def mark_all_as_read(self, client_id: int) -> int:
        """Mark all notifications as read for a client"""
        count = ClientNotification.query.filter_by(client_id=client_id, is_read=False).update(
            {"is_read": True, "read_at": datetime.utcnow()}
        )
        db.session.commit()
        return count

    def get_unread_count(self, client_id: int) -> int:
        """Get unread notification count"""
        return ClientNotification.get_unread_count(client_id)

    def get_notifications(self, client_id: int, limit: int = 50, unread_only: bool = False) -> List[ClientNotification]:
        """Get notifications for a client"""
        query = ClientNotification.query.filter_by(client_id=client_id)
        if unread_only:
            query = query.filter_by(is_read=False)
        return query.order_by(ClientNotification.created_at.desc()).limit(limit).all()
