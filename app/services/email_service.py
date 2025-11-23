"""
Service for email operations.
"""

from typing import Dict, Any, Optional, List
from flask import current_app, render_template
from app.utils.email import send_email
from app.repositories import InvoiceRepository
from app.models import Invoice


class EmailService:
    """Service for email operations"""
    
    def __init__(self):
        self.invoice_repo = InvoiceRepository()
    
    def send_invoice_email(
        self,
        invoice_id: int,
        recipient_email: str,
        subject: Optional[str] = None,
        message: Optional[str] = None,
        attach_pdf: bool = True
    ) -> Dict[str, Any]:
        """
        Send an invoice via email.
        
        Returns:
            dict with 'success' and 'message' keys
        """
        invoice = self.invoice_repo.get_with_relations(invoice_id)
        
        if not invoice:
            return {
                'success': False,
                'message': 'Invoice not found',
                'error': 'not_found'
            }
        
        # Generate subject if not provided
        if not subject:
            subject = f"Invoice {invoice.invoice_number} from {current_app.config.get('COMPANY_NAME', 'TimeTracker')}"
        
        # Render email template
        try:
            html_body = render_template(
                'email/invoice.html',
                invoice=invoice,
                message=message
            )
        except Exception:
            # Fallback to simple text
            html_body = f"""
            <p>Dear {invoice.client_name},</p>
            <p>Please find attached invoice {invoice.invoice_number}.</p>
            <p>Total: {invoice.currency_code} {invoice.total_amount}</p>
            <p>Due Date: {invoice.due_date}</p>
            """
            if message:
                html_body += f"<p>{message}</p>"
        
        # Send email
        try:
            send_email(
                subject=subject,
                recipients=[recipient_email],
                text_body=message or f"Invoice {invoice.invoice_number}",
                html_body=html_body,
                attachments=[]  # PDF attachment would be added here
            )
            
            # Mark invoice as sent
            self.invoice_repo.mark_as_sent(invoice_id)
            
            return {
                'success': True,
                'message': 'Invoice email sent successfully'
            }
        
        except Exception as e:
            current_app.logger.error(f"Failed to send invoice email: {e}")
            return {
                'success': False,
                'message': f'Failed to send email: {str(e)}',
                'error': 'email_error'
            }
    
    def send_notification_email(
        self,
        recipient_email: str,
        subject: str,
        message: str,
        template: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a notification email.
        
        Returns:
            dict with 'success' and 'message' keys
        """
        try:
            if template:
                html_body = render_template(template, **(context or {}))
            else:
                html_body = f"<p>{message}</p>"
            
            send_email(
                subject=subject,
                recipients=[recipient_email],
                text_body=message,
                html_body=html_body
            )
            
            return {
                'success': True,
                'message': 'Notification email sent successfully'
            }
        
        except Exception as e:
            current_app.logger.error(f"Failed to send notification email: {e}")
            return {
                'success': False,
                'message': f'Failed to send email: {str(e)}',
                'error': 'email_error'
            }

