"""Email utilities for sending notifications and reports"""

import os
from flask import current_app, render_template, url_for
from jinja2 import Template as JinjaTemplate
from flask_mail import Mail, Message
from threading import Thread
from datetime import datetime, timedelta
from app import db


mail = Mail()


def init_mail(app):
    """Initialize Flask-Mail with the app

    Checks for database settings first, then falls back to environment variables.
    Database settings persist between restarts and updates.
    """
    # First, load defaults from environment variables (as fallback)
    app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "localhost")
    app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    app.config["MAIL_USE_SSL"] = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", "noreply@timetracker.local")
    app.config["MAIL_MAX_EMAILS"] = int(os.getenv("MAIL_MAX_EMAILS", 100))

    # Check if database settings should override environment variables
    # Database settings persist between restarts and updates
    try:
        from app.models import Settings
        from app import db

        if db.session.is_active:
            settings = Settings.get_settings()
            db_config = settings.get_mail_config()

            if db_config:
                # Database settings take precedence and persist between restarts
                app.config.update(db_config)
                app.logger.info(
                    f"✓ Using database email configuration (persistent): {db_config.get('MAIL_SERVER')}:{db_config.get('MAIL_PORT')}"
                )
            else:
                app.logger.info("Using environment variable email configuration (database email not enabled)")
    except Exception as e:
        # If database is not available, fall back to environment variables
        app.logger.debug(f"Could not load email settings from database: {e}")
        app.logger.info("Using environment variable email configuration (database unavailable)")

    mail.init_app(app)
    return mail


def reload_mail_config(app):
    """Reload email configuration from database

    Call this after updating email settings in the database to apply changes.
    Database settings persist between restarts and updates.
    """
    try:
        from app.models import Settings

        settings = Settings.get_settings()
        db_config = settings.get_mail_config()

        if db_config:
            # Update app configuration with latest database settings
            app.config.update(db_config)
            # Reinitialize mail with new config (this ensures mail object uses latest settings)
            mail.init_app(app)
            app.logger.info(
                f"✓ Email configuration reloaded from database: {db_config.get('MAIL_SERVER')}:{db_config.get('MAIL_PORT')}"
            )
            return True
        else:
            app.logger.info("No database email configuration found, using environment variables")
            return False
    except Exception as e:
        app.logger.error(f"Failed to reload email configuration: {e}")
        return False


def send_async_email(app, msg):
    """Send email asynchronously in background thread"""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            current_app.logger.error(f"Failed to send email: {e}")


def send_client_portal_password_setup_email(client, token):
    """Send password setup email to client

    Args:
        client: Client object
        token: Password setup token

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        if not client.email:
            current_app.logger.warning(f"Cannot send password setup email to client {client.name}: no email address")
            return False

        # Always check database settings first (they take precedence)
        from app.models import Settings

        settings = Settings.get_settings()
        db_config = settings.get_mail_config()

        # Use database config if available, otherwise fall back to app config
        if db_config:
            mail_server = db_config.get("MAIL_SERVER")
            mail_default_sender = db_config.get("MAIL_DEFAULT_SENDER")
            # Reload mail config to ensure we're using latest database settings
            reload_mail_config(current_app._get_current_object())
        else:
            mail_server = current_app.config.get("MAIL_SERVER")
            mail_default_sender = current_app.config.get("MAIL_DEFAULT_SENDER")

        # Check if email is configured
        if not mail_server or mail_server == "localhost":
            current_app.logger.error("Mail server not configured. Cannot send password setup email.")
            return False

        # Generate password setup URL
        setup_url = url_for("client_portal.set_password", token=token, _external=True)

        # Render email template
        html_body = render_template(
            "email/client_portal_password_setup.html", client=client, setup_url=setup_url, token=token
        )

        # Plain text version
        text_body = f"""
Hello {client.name or client.contact_person or 'Client'},

You have been granted access to the TimeTracker Client Portal.

To set your password and access the portal, please click the following link:
{setup_url}

This link will expire in 24 hours.

If you did not request this access, please contact your administrator.

Best regards,
TimeTracker Team
"""

        subject = f"Set Your Client Portal Password - {client.name}"

        # Create message
        msg = Message(
            subject=subject,
            recipients=[client.email],
            body=text_body,
            html=html_body,
            sender=mail_default_sender or current_app.config.get("MAIL_DEFAULT_SENDER", "noreply@timetracker.local"),
        )

        # Send synchronously to catch errors
        try:
            mail.send(msg)
            current_app.logger.info(
                f"Password setup email sent successfully to {client.email} for client {client.name}"
            )
            return True
        except Exception as send_error:
            current_app.logger.error(f"Failed to send password setup email: {send_error}")
            return False

    except Exception as e:
        current_app.logger.error(f"Failed to prepare password setup email: {e}")
        return False


def send_email(subject, recipients, text_body, html_body=None, sender=None, attachments=None):
    """Send an email

    Args:
        subject: Email subject line
        recipients: List of recipient email addresses
        text_body: Plain text email body
        html_body: HTML email body (optional)
        sender: Sender email address (optional, uses default if not provided)
        attachments: List of (filename, content_type, data) tuples
    """
    # Always check database settings first (they take precedence)
    from app.models import Settings

    settings = Settings.get_settings()
    db_config = settings.get_mail_config()

    # Use database config if available, otherwise fall back to app config
    if db_config:
        mail_server = db_config.get("MAIL_SERVER")
        mail_default_sender = db_config.get("MAIL_DEFAULT_SENDER")
    else:
        mail_server = current_app.config.get("MAIL_SERVER")
        mail_default_sender = current_app.config.get("MAIL_DEFAULT_SENDER")

    if not mail_server or mail_server == "localhost":
        current_app.logger.warning("Mail server not configured, skipping email send")
        return

    if not recipients:
        current_app.logger.warning("No recipients specified for email")
        return

    msg = Message(
        subject=subject,
        recipients=recipients if isinstance(recipients, list) else [recipients],
        body=text_body,
        html=html_body,
        sender=sender
        or mail_default_sender
        or current_app.config.get("MAIL_DEFAULT_SENDER", "noreply@timetracker.local"),
    )

    # Add attachments if provided
    if attachments:
        for filename, content_type, data in attachments:
            msg.attach(filename, content_type, data)

    # Send asynchronously
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()


def send_overdue_invoice_notification(invoice, user):
    """Send notification about an overdue invoice

    Args:
        invoice: Invoice object
        user: User object (invoice creator or admin)
    """
    if not user.email or not user.email_notifications or not user.notification_overdue_invoices:
        return

    days_overdue = (datetime.utcnow().date() - invoice.due_date).days

    subject = f"Invoice {invoice.invoice_number} is {days_overdue} days overdue"

    text_body = f"""
Hello {user.display_name},

Invoice {invoice.invoice_number} for {invoice.client_name} is now {days_overdue} days overdue.

Invoice Details:
- Invoice Number: {invoice.invoice_number}
- Client: {invoice.client_name}
- Amount: {invoice.currency_code} {invoice.total_amount}
- Due Date: {invoice.due_date}
- Days Overdue: {days_overdue}

Please follow up with the client or update the invoice status.

View invoice: {url_for('invoices.view_invoice', invoice_id=invoice.id, _external=True)}

---
TimeTracker - Time Tracking & Project Management
    """

    html_body = render_template("email/overdue_invoice.html", user=user, invoice=invoice, days_overdue=days_overdue)

    send_email(subject, user.email, text_body, html_body)


def send_task_assigned_notification(task, user, assigned_by):
    """Send notification when a user is assigned to a task

    Args:
        task: Task object
        user: User who was assigned
        assigned_by: User who made the assignment
    """
    if not user.email or not user.email_notifications or not user.notification_task_assigned:
        return

    subject = f"You've been assigned to task: {task.name}"

    text_body = f"""
Hello {user.display_name},

{assigned_by.display_name} has assigned you to a task.

Task Details:
- Task: {task.name}
- Project: {task.project.name if task.project else 'N/A'}
- Priority: {task.priority or 'Normal'}
- Due Date: {task.due_date if task.due_date else 'Not set'}
- Status: {task.status}

Description:
{task.description or 'No description provided'}

View task: {url_for('tasks.edit_task', task_id=task.id, _external=True)}

---
TimeTracker - Time Tracking & Project Management
    """

    html_body = render_template("email/task_assigned.html", user=user, task=task, assigned_by=assigned_by)

    send_email(subject, user.email, text_body, html_body)


def send_weekly_summary(user, start_date, end_date, hours_worked, projects_data):
    """Send weekly time tracking summary to user

    Args:
        user: User object
        start_date: Start of the week
        end_date: End of the week
        hours_worked: Total hours worked
        projects_data: List of dicts with project data
    """
    if not user.email or not user.email_notifications or not user.notification_weekly_summary:
        return

    subject = f"Your Weekly Time Summary ({start_date} to {end_date})"

    # Build project summary text
    project_summary = "\n".join([f"- {p['name']}: {p['hours']:.1f} hours" for p in projects_data])

    text_body = f"""
Hello {user.display_name},

Here's your time tracking summary for the week of {start_date} to {end_date}:

Total Hours: {hours_worked:.1f}

Hours by Project:
{project_summary}

Keep up the great work!

View detailed reports: {url_for('reports.reports', _external=True)}

---
TimeTracker - Time Tracking & Project Management
    """

    html_body = render_template(
        "email/weekly_summary.html",
        user=user,
        start_date=start_date,
        end_date=end_date,
        hours_worked=hours_worked,
        projects_data=projects_data,
    )

    send_email(subject, user.email, text_body, html_body)


def send_comment_notification(comment, task, mentioned_users):
    """Send notification about a new comment

    Args:
        comment: Comment object
        task: Task the comment is on
        mentioned_users: List of User objects mentioned in the comment
    """
    for user in mentioned_users:
        if not user.email or not user.email_notifications or not user.notification_task_comments:
            continue

        subject = f"You were mentioned in a comment on: {task.name}"

        text_body = f"""
Hello {user.display_name},

{comment.user.display_name} mentioned you in a comment on task "{task.name}".

Comment:
{comment.content}

Task: {task.name}
Project: {task.project.name if task.project else 'N/A'}

View task: {url_for('tasks.edit_task', task_id=task.id, _external=True)}

---
TimeTracker - Time Tracking & Project Management
        """

        html_body = render_template("email/comment_mention.html", user=user, comment=comment, task=task)

        send_email(subject, user.email, text_body, html_body)


def check_email_configuration():
    """Check email configuration and return status

    Returns:
        dict: Status information with 'configured', 'settings', 'errors', 'source' keys
    """
    status = {
        "configured": False,
        "settings": {},
        "errors": [],
        "warnings": [],
        "source": "environment",  # or 'database'
    }

    # Check if database configuration is enabled
    try:
        from app.models import Settings

        settings = Settings.get_settings()
        if settings.mail_enabled and settings.mail_server:
            status["source"] = "database"
            mail_server = settings.mail_server
            mail_port = settings.mail_port
            mail_username = settings.mail_username
            mail_password = settings.mail_password
            mail_use_tls = settings.mail_use_tls
            mail_use_ssl = settings.mail_use_ssl
            mail_default_sender = settings.mail_default_sender
        else:
            # Use environment/app config
            mail_server = current_app.config.get("MAIL_SERVER")
            mail_port = current_app.config.get("MAIL_PORT")
            mail_username = current_app.config.get("MAIL_USERNAME")
            mail_password = current_app.config.get("MAIL_PASSWORD")
            mail_use_tls = current_app.config.get("MAIL_USE_TLS")
            mail_use_ssl = current_app.config.get("MAIL_USE_SSL")
            mail_default_sender = current_app.config.get("MAIL_DEFAULT_SENDER")
    except Exception:
        # Fall back to app config if database not available
        mail_server = current_app.config.get("MAIL_SERVER")
        mail_port = current_app.config.get("MAIL_PORT")
        mail_username = current_app.config.get("MAIL_USERNAME")
        mail_password = current_app.config.get("MAIL_PASSWORD")
        mail_use_tls = current_app.config.get("MAIL_USE_TLS")
        mail_use_ssl = current_app.config.get("MAIL_USE_SSL")
        mail_default_sender = current_app.config.get("MAIL_DEFAULT_SENDER")

    status["settings"] = {
        "server": mail_server or "Not configured",
        "port": mail_port or "Not configured",
        "username": mail_username or "Not configured",
        "password_set": bool(mail_password),
        "use_tls": mail_use_tls,
        "use_ssl": mail_use_ssl,
        "default_sender": mail_default_sender or "Not configured",
    }

    # Check for configuration issues
    if not mail_server or mail_server == "localhost":
        status["errors"].append("Mail server not configured or set to localhost")

    if not mail_default_sender or mail_default_sender == "noreply@timetracker.local":
        status["warnings"].append("Default sender email should be configured with a real email address")

    if mail_use_tls and mail_use_ssl:
        status["errors"].append("Cannot use both TLS and SSL. Choose one.")

    if not mail_username and mail_server not in ["localhost", "127.0.0.1"]:
        status["warnings"].append("MAIL_USERNAME not set (may be required for authentication)")

    if not mail_password and mail_username:
        status["warnings"].append("MAIL_PASSWORD not set but MAIL_USERNAME is configured")

    # Mark as configured if minimum requirements are met
    status["configured"] = bool(mail_server and mail_server != "localhost" and not status["errors"])

    return status


def send_test_email(recipient_email, sender_name="TimeTracker Admin"):
    """Send a test email to verify email configuration

    Args:
        recipient_email: Email address to send test email to
        sender_name: Name of the sender

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        current_app.logger.info(f"[EMAIL TEST] Starting test email send to: {recipient_email}")

        # Validate recipient email
        if not recipient_email or "@" not in recipient_email:
            current_app.logger.warning(f"[EMAIL TEST] Invalid recipient email: {recipient_email}")
            return False, "Invalid recipient email address"

        # Check if mail is configured
        mail_server = current_app.config.get("MAIL_SERVER")
        if not mail_server:
            current_app.logger.error("[EMAIL TEST] Mail server not configured")
            return False, "Mail server not configured. Please set MAIL_SERVER in environment variables."

        # Log current configuration
        current_app.logger.info(f"[EMAIL TEST] Configuration:")
        current_app.logger.info(f"  - Server: {mail_server}:{current_app.config.get('MAIL_PORT')}")
        current_app.logger.info(f"  - TLS: {current_app.config.get('MAIL_USE_TLS')}")
        current_app.logger.info(f"  - SSL: {current_app.config.get('MAIL_USE_SSL')}")
        current_app.logger.info(f"  - Username: {current_app.config.get('MAIL_USERNAME')}")
        current_app.logger.info(f"  - Sender: {current_app.config.get('MAIL_DEFAULT_SENDER')}")

        subject = "TimeTracker Email Test"

        text_body = f"""
Hello,

This is a test email from TimeTracker to verify your email configuration is working correctly.

If you received this email, your email settings are properly configured!

Test Details:
- Sent at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
- Sent by: {sender_name}
- Mail Server: {current_app.config.get('MAIL_SERVER')}:{current_app.config.get('MAIL_PORT')}
- TLS Enabled: {current_app.config.get('MAIL_USE_TLS')}
- SSL Enabled: {current_app.config.get('MAIL_USE_SSL')}

---
TimeTracker - Time Tracking & Project Management
        """

        try:
            html_body = render_template(
                "email/test_email.html",
                sender_name=sender_name,
                mail_server=current_app.config.get("MAIL_SERVER"),
                mail_port=current_app.config.get("MAIL_PORT"),
                use_tls=current_app.config.get("MAIL_USE_TLS"),
                use_ssl=current_app.config.get("MAIL_USE_SSL"),
                datetime=datetime,
            )
            current_app.logger.info("[EMAIL TEST] HTML template rendered successfully")
        except Exception as template_error:
            # If template doesn't exist, use text only
            current_app.logger.warning(f"[EMAIL TEST] HTML template not available: {template_error}")
            html_body = None

        # Create message
        current_app.logger.info("[EMAIL TEST] Creating email message")
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            body=text_body,
            html=html_body,
            sender=current_app.config["MAIL_DEFAULT_SENDER"],
        )

        # Send synchronously for testing (so we can catch errors)
        current_app.logger.info("[EMAIL TEST] Attempting to send email via SMTP...")
        mail.send(msg)
        current_app.logger.info(f"[EMAIL TEST] ✓ Email sent successfully to {recipient_email}")

        return True, f"Test email sent successfully to {recipient_email}"

    except Exception as e:
        current_app.logger.error(f"[EMAIL TEST] ✗ Failed to send test email: {type(e).__name__}: {str(e)}")
        current_app.logger.exception("[EMAIL TEST] Full exception trace:")
        return False, f"Failed to send test email: {str(e)}"


def send_invoice_email(invoice, recipient_email, sender_user=None, custom_message=None, email_template_id=None):
    """Send an invoice via email with PDF attachment

    Args:
        invoice: Invoice object
        recipient_email: Email address to send to
        sender_user: User object who is sending (for tracking)
        custom_message: Optional custom message to include in email
        email_template_id: Optional email template ID to use

    Returns:
        tuple: (success: bool, invoice_email: InvoiceEmail or None, message: str)
    """
    try:
        from app.models import InvoiceEmail, Settings

        current_app.logger.info(f"[INVOICE EMAIL] Sending invoice {invoice.invoice_number} to {recipient_email}")

        # Generate PDF
        pdf_bytes = None
        try:
            from app.utils.pdf_generator import InvoicePDFGenerator

            settings = Settings.get_settings()
            pdf_generator = InvoicePDFGenerator(invoice, settings=settings, page_size="A4")
            pdf_bytes = pdf_generator.generate_pdf()
            if not pdf_bytes:
                raise ValueError("PDF generator returned None")
            current_app.logger.info(f"[INVOICE EMAIL] PDF generated successfully - size: {len(pdf_bytes)} bytes")
        except Exception as pdf_error:
            current_app.logger.warning(f"[INVOICE EMAIL] PDF generation failed, trying fallback: {pdf_error}")
            current_app.logger.exception("[INVOICE EMAIL] PDF generation error details:")
            try:
                from app.utils.pdf_generator_fallback import InvoicePDFGeneratorFallback

                settings = Settings.get_settings()
                pdf_generator = InvoicePDFGeneratorFallback(invoice, settings=settings)
                pdf_bytes = pdf_generator.generate_pdf()
                if not pdf_bytes:
                    raise ValueError("PDF fallback generator returned None")
                current_app.logger.info(f"[INVOICE EMAIL] PDF generated via fallback - size: {len(pdf_bytes)} bytes")
            except Exception as fallback_error:
                current_app.logger.error(f"[INVOICE EMAIL] Both PDF generators failed: {fallback_error}")
                current_app.logger.exception("[INVOICE EMAIL] Fallback PDF generation error details:")
                return False, None, f"PDF generation failed: {str(fallback_error)}"

        if not pdf_bytes:
            current_app.logger.error("[INVOICE EMAIL] PDF bytes is None after generation")
            return False, None, "PDF generation returned empty result"

        # Get settings for email subject/body
        settings = Settings.get_settings()
        company_name = settings.company_name if settings else "Your Company"

        # Create email subject
        subject = f"Invoice {invoice.invoice_number} from {company_name}"

        # Get email template if specified
        html_body = None
        text_body = None

        if email_template_id:
            try:
                from app.models import InvoiceTemplate

                email_template = InvoiceTemplate.query.get(email_template_id)
                if email_template and email_template.html:
                    # Use custom template
                    # Ensure the HTML is properly formatted for email
                    template_html = email_template.html.strip()

                    # If CSS is provided separately, wrap it in <style> tags
                    if email_template.css and email_template.css.strip():
                        css_content = email_template.css.strip()
                        # Check if CSS is already wrapped in <style> tags
                        if not css_content.startswith("<style"):
                            css_content = f"<style>\n{css_content}\n</style>"
                        # Insert CSS into HTML if not already present
                        if "<style>" not in template_html and "</style>" not in template_html:
                            # Try to insert before </head> or at the beginning if no head tag
                            if "</head>" in template_html:
                                template_html = template_html.replace("</head>", f"{css_content}\n</head>")
                            elif "<body>" in template_html:
                                template_html = template_html.replace("<body>", f"{css_content}\n<body>")
                            else:
                                template_html = f"{css_content}\n{template_html}"

                    # Ensure HTML has proper structure
                    if not template_html.strip().startswith("<!DOCTYPE") and not template_html.strip().startswith(
                        "<html"
                    ):
                        # Wrap in minimal HTML structure if needed
                        if "<html" not in template_html:
                            template_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body>
{template_html}
</body>
</html>"""

                    template = JinjaTemplate(template_html)
                    html_body = template.render(
                        invoice=invoice, company_name=company_name, custom_message=custom_message
                    )
                    # Generate text version from HTML if needed
                    text_body = f"Invoice {invoice.invoice_number} - Please see attached PDF for details."
            except Exception as template_error:
                current_app.logger.warning(f"[INVOICE EMAIL] Custom template failed: {template_error}")
                current_app.logger.exception("[INVOICE EMAIL] Template error details:")

        # Fallback to default template
        if not html_body:
            # Create email body
            text_body = f"""
Hello,

Please find attached invoice {invoice.invoice_number} for your records.

Invoice Details:
- Invoice Number: {invoice.invoice_number}
- Issue Date: {invoice.issue_date.strftime('%Y-%m-%d') if invoice.issue_date else 'N/A'}
- Due Date: {invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else 'N/A'}
- Amount: {invoice.currency_code} {invoice.total_amount}

"""

            if custom_message:
                text_body += f"\n{custom_message}\n\n"

            text_body += f"""
Please remit payment by the due date.

Thank you for your business!

---
{company_name}
"""

            # Render HTML template
            try:
                html_body = render_template(
                    "email/invoice.html", invoice=invoice, company_name=company_name, custom_message=custom_message
                )
            except Exception as template_error:
                current_app.logger.warning(f"[INVOICE EMAIL] HTML template not available: {template_error}")
                html_body = None

        # Get sender user ID
        sender_id = sender_user.id if sender_user else None
        if not sender_id:
            # Try to get from invoice creator
            sender_id = invoice.created_by

        # Filename should be template+date+number (invoice number format)
        # Send email synchronously to catch errors
        attachments = [(f"{invoice.invoice_number}.pdf", "application/pdf", pdf_bytes)]

        # Create message
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            body=text_body,
            html=html_body,
            sender=current_app.config["MAIL_DEFAULT_SENDER"],
        )

        # Add attachments
        for filename, content_type, data in attachments:
            msg.attach(filename, content_type, data)

        # Send synchronously to catch errors
        try:
            current_app.logger.info(f"[INVOICE EMAIL] Attempting to send email to {recipient_email}")
            current_app.logger.debug(
                f"[INVOICE EMAIL] Email config - Server: {current_app.config.get('MAIL_SERVER')}, Port: {current_app.config.get('MAIL_PORT')}"
            )
            mail.send(msg)
            current_app.logger.info(f"[INVOICE EMAIL] ✓ Email sent successfully to {recipient_email}")
        except Exception as send_error:
            current_app.logger.error(
                f"[INVOICE EMAIL] ✗ Failed to send email: {type(send_error).__name__}: {str(send_error)}"
            )
            current_app.logger.exception("[INVOICE EMAIL] Email send error details:")
            raise send_error

        # Create email tracking record
        invoice_email = InvoiceEmail(
            invoice_id=invoice.id, recipient_email=recipient_email, subject=subject, sent_by=sender_id
        )
        db.session.add(invoice_email)

        # Update invoice status to 'sent' if it's still 'draft'
        if invoice.status == "draft":
            invoice.status = "sent"

        db.session.commit()

        return True, invoice_email, f"Invoice email sent successfully to {recipient_email}"

    except Exception as e:
        current_app.logger.error(f"[INVOICE EMAIL] ✗ Failed to send invoice email: {type(e).__name__}: {str(e)}")
        current_app.logger.exception("[INVOICE EMAIL] Full exception trace:")

        # Try to create failed tracking record
        try:
            from app.models import InvoiceEmail

            sender_id = sender_user.id if sender_user else invoice.created_by
            invoice_email = InvoiceEmail(
                invoice_id=invoice.id,
                recipient_email=recipient_email,
                subject=f"Invoice {invoice.invoice_number}",
                sent_by=sender_id,
            )
            invoice_email.mark_failed(str(e))
            db.session.add(invoice_email)
            db.session.commit()
        except Exception:
            db.session.rollback()

        return False, None, f"Failed to send invoice email: {str(e)}"


def send_quote_sent_notification(quote, user):
    """Send notification when a quote is sent to client

    Args:
        quote: Quote object
        user: User object (quote creator or admin)
    """
    if not user.email or not user.email_notifications:
        return

    subject = f"Quote {quote.quote_number} has been sent to {quote.client.name if quote.client else 'client'}"

    text_body = f"""
Hello {user.display_name or user.username},

Quote {quote.quote_number} has been sent to the client.

Quote Details:
- Quote Number: {quote.quote_number}
- Title: {quote.title}
- Client: {quote.client.name if quote.client else 'N/A'}
- Total Amount: {quote.currency_code} {quote.total_amount}
- Sent At: {quote.sent_at.strftime('%Y-%m-%d %H:%M') if quote.sent_at else 'N/A'}

View quote: {url_for('quotes.view_quote', quote_id=quote.id, _external=True)}

---
TimeTracker - Time Tracking & Project Management
    """

    html_body = render_template("email/quote_sent.html", user=user, quote=quote)

    send_email(subject, user.email, text_body, html_body)


def send_quote_accepted_notification(quote, user):
    """Send notification when a quote is accepted

    Args:
        quote: Quote object
        user: User object (quote creator or admin)
    """
    if not user.email or not user.email_notifications:
        return

    subject = f"Quote {quote.quote_number} has been accepted"

    text_body = f"""
Hello {user.display_name or user.username},

Great news! Quote {quote.quote_number} has been accepted by the client.

Quote Details:
- Quote Number: {quote.quote_number}
- Title: {quote.title}
- Client: {quote.client.name if quote.client else 'N/A'}
- Total Amount: {quote.currency_code} {quote.total_amount}
- Accepted At: {quote.accepted_at.strftime('%Y-%m-%d %H:%M') if quote.accepted_at else 'N/A'}
- Project: {'Created' if quote.has_project else 'Not yet created'}

View quote: {url_for('quotes.view_quote', quote_id=quote.id, _external=True)}

---
TimeTracker - Time Tracking & Project Management
    """

    html_body = render_template("email/quote_accepted.html", user=user, quote=quote)

    send_email(subject, user.email, text_body, html_body)


def send_quote_rejected_notification(quote, user):
    """Send notification when a quote is rejected

    Args:
        quote: Quote object
        user: User object (quote creator or admin)
    """
    if not user.email or not user.email_notifications:
        return

    subject = f"Quote {quote.quote_number} has been rejected"

    text_body = f"""
Hello {user.display_name or user.username},

Quote {quote.quote_number} has been rejected by the client.

Quote Details:
- Quote Number: {quote.quote_number}
- Title: {quote.title}
- Client: {quote.client.name if quote.client else 'N/A'}
- Total Amount: {quote.currency_code} {quote.total_amount}
- Rejected At: {quote.rejected_at.strftime('%Y-%m-%d %H:%M') if quote.rejected_at else 'N/A'}

View quote: {url_for('quotes.view_quote', quote_id=quote.id, _external=True)}

---
TimeTracker - Time Tracking & Project Management
    """

    html_body = render_template("email/quote_rejected.html", user=user, quote=quote)

    send_email(subject, user.email, text_body, html_body)


def send_quote_expired_notification(quote, user):
    """Send notification when a quote expires

    Args:
        quote: Quote object
        user: User object (quote creator or admin)
    """
    if not user.email or not user.email_notifications:
        return

    subject = f"Quote {quote.quote_number} has expired"

    text_body = f"""
Hello {user.display_name or user.username},

Quote {quote.quote_number} has expired.

Quote Details:
- Quote Number: {quote.quote_number}
- Title: {quote.title}
- Client: {quote.client.name if quote.client else 'N/A'}
- Total Amount: {quote.currency_code} {quote.total_amount}
- Valid Until: {quote.valid_until.strftime('%Y-%m-%d') if quote.valid_until else 'N/A'}

You may want to follow up with the client or create a new quote.

View quote: {url_for('quotes.view_quote', quote_id=quote.id, _external=True)}

---
TimeTracker - Time Tracking & Project Management
    """

    html_body = render_template("email/quote_expired.html", user=user, quote=quote)

    send_email(subject, user.email, text_body, html_body)


def send_quote_email(quote, recipient_email, sender_user=None, custom_message=None):
    """Send a quote via email with PDF attachment

    Args:
        quote: Quote object
        recipient_email: Email address to send to
        sender_user: User object who is sending (for tracking)
        custom_message: Optional custom message to include in email

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        from app.models import Settings
        from flask import current_app
        from flask_mail import Message
        from flask import render_template
        from app import mail, db

        current_app.logger.info(f"[QUOTE EMAIL] Sending quote {quote.quote_number} to {recipient_email}")

        # Generate PDF
        pdf_bytes = None
        try:
            # Try to use QuotePDFGenerator if it exists
            try:
                from app.utils.pdf_generator import QuotePDFGenerator

                settings = Settings.get_settings()
                pdf_generator = QuotePDFGenerator(quote, settings=settings, page_size="A4")
                pdf_bytes = pdf_generator.generate_pdf()
            except ImportError:
                # Fallback to simple PDF generation
                from app.utils.pdf_generator_fallback import QuotePDFGeneratorFallback

                settings = Settings.get_settings()
                pdf_generator = QuotePDFGeneratorFallback(quote, settings=settings)
                pdf_bytes = pdf_generator.generate_pdf()

            if not pdf_bytes:
                raise ValueError("PDF generator returned None")
            current_app.logger.info(f"[QUOTE EMAIL] PDF generated successfully - size: {len(pdf_bytes)} bytes")
        except Exception as pdf_error:
            current_app.logger.error(f"[QUOTE EMAIL] PDF generation failed: {pdf_error}")
            current_app.logger.exception("[QUOTE EMAIL] PDF generation error details:")
            return False, f"PDF generation failed: {str(pdf_error)}"

        # Get settings for email subject/body
        settings = Settings.get_settings()
        company_name = settings.company_name if settings else "Your Company"

        # Create email subject
        subject = f"Quote {quote.quote_number} from {company_name}"

        # Create email body
        text_body = f"""
Hello,

Please find attached quote {quote.quote_number} for your review.

Quote Details:
- Quote Number: {quote.quote_number}
- Title: {quote.title}
- Valid Until: {quote.valid_until.strftime('%Y-%m-%d') if quote.valid_until else 'N/A'}
- Amount: {quote.currency_code} {quote.total_amount}

"""

        if custom_message:
            text_body += f"\n{custom_message}\n\n"

        text_body += f"""
Please review the attached quote and let us know if you have any questions.

Thank you for your interest!

---
{company_name}
"""

        # Render HTML template
        html_body = None
        try:
            html_body = render_template(
                "email/quote.html", quote=quote, company_name=company_name, custom_message=custom_message
            )
        except Exception as template_error:
            current_app.logger.warning(f"[QUOTE EMAIL] HTML template not available: {template_error}")
            html_body = None

        # Send email synchronously to catch errors
        attachments = [(f"quote_{quote.quote_number}.pdf", "application/pdf", pdf_bytes)]

        # Create message
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            body=text_body,
            html=html_body,
            sender=current_app.config["MAIL_DEFAULT_SENDER"],
        )

        # Add attachments
        for filename, content_type, data in attachments:
            msg.attach(filename, content_type, data)

        # Send synchronously to catch errors
        try:
            current_app.logger.info(f"[QUOTE EMAIL] Attempting to send email to {recipient_email}")
            mail.send(msg)
            current_app.logger.info(f"[QUOTE EMAIL] ✓ Email sent successfully to {recipient_email}")
        except Exception as send_error:
            current_app.logger.error(
                f"[QUOTE EMAIL] ✗ Failed to send email: {type(send_error).__name__}: {str(send_error)}"
            )
            current_app.logger.exception("[QUOTE EMAIL] Email send error details:")
            raise send_error

        # Mark quote as sent if it's still draft
        if quote.status == "draft":
            quote.send()
            db.session.commit()

        return True, "Email sent successfully"
    except Exception as e:
        current_app.logger.error(f"[QUOTE EMAIL] Exception in send_quote_email: {e}", exc_info=True)
        db.session.rollback()
        return False, f"Failed to send email: {str(e)}"
