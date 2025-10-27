"""Email utilities for sending notifications and reports"""

import os
from flask import current_app, render_template, url_for
from flask_mail import Mail, Message
from threading import Thread
from datetime import datetime, timedelta


mail = Mail()


def init_mail(app):
    """Initialize Flask-Mail with the app
    
    Checks for database settings first, then falls back to environment variables.
    """
    # First, load defaults from environment variables
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'localhost')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@timetracker.local')
    app.config['MAIL_MAX_EMAILS'] = int(os.getenv('MAIL_MAX_EMAILS', 100))
    
    # Check if database settings should override environment variables
    try:
        from app.models import Settings
        from app import db
        
        if db.session.is_active:
            settings = Settings.get_settings()
            db_config = settings.get_mail_config()
            
            if db_config:
                # Database settings take precedence
                app.config.update(db_config)
                app.logger.info("Using database email configuration")
            else:
                app.logger.info("Using environment variable email configuration")
    except Exception as e:
        # If database is not available, fall back to environment variables
        app.logger.debug(f"Could not load email settings from database: {e}")
    
    mail.init_app(app)
    return mail


def reload_mail_config(app):
    """Reload email configuration from database
    
    Call this after updating email settings in the database to apply changes.
    """
    try:
        from app.models import Settings
        settings = Settings.get_settings()
        db_config = settings.get_mail_config()
        
        if db_config:
            # Update app configuration
            app.config.update(db_config)
            # Reinitialize mail with new config
            mail.init_app(app)
            return True
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
    if not current_app.config.get('MAIL_SERVER'):
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
        sender=sender or current_app.config['MAIL_DEFAULT_SENDER']
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
    
    html_body = render_template(
        'email/overdue_invoice.html',
        user=user,
        invoice=invoice,
        days_overdue=days_overdue
    )
    
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
    
    html_body = render_template(
        'email/task_assigned.html',
        user=user,
        task=task,
        assigned_by=assigned_by
    )
    
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
    project_summary = "\n".join([
        f"- {p['name']}: {p['hours']:.1f} hours"
        for p in projects_data
    ])
    
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
        'email/weekly_summary.html',
        user=user,
        start_date=start_date,
        end_date=end_date,
        hours_worked=hours_worked,
        projects_data=projects_data
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
        
        html_body = render_template(
            'email/comment_mention.html',
            user=user,
            comment=comment,
            task=task
        )
        
        send_email(subject, user.email, text_body, html_body)


def test_email_configuration():
    """Test email configuration and return status
    
    Returns:
        dict: Status information with 'configured', 'settings', 'errors', 'source' keys
    """
    status = {
        'configured': False,
        'settings': {},
        'errors': [],
        'warnings': [],
        'source': 'environment'  # or 'database'
    }
    
    # Check if database configuration is enabled
    try:
        from app.models import Settings
        settings = Settings.get_settings()
        if settings.mail_enabled and settings.mail_server:
            status['source'] = 'database'
            mail_server = settings.mail_server
            mail_port = settings.mail_port
            mail_username = settings.mail_username
            mail_password = settings.mail_password
            mail_use_tls = settings.mail_use_tls
            mail_use_ssl = settings.mail_use_ssl
            mail_default_sender = settings.mail_default_sender
        else:
            # Use environment/app config
            mail_server = current_app.config.get('MAIL_SERVER')
            mail_port = current_app.config.get('MAIL_PORT')
            mail_username = current_app.config.get('MAIL_USERNAME')
            mail_password = current_app.config.get('MAIL_PASSWORD')
            mail_use_tls = current_app.config.get('MAIL_USE_TLS')
            mail_use_ssl = current_app.config.get('MAIL_USE_SSL')
            mail_default_sender = current_app.config.get('MAIL_DEFAULT_SENDER')
    except Exception:
        # Fall back to app config if database not available
        mail_server = current_app.config.get('MAIL_SERVER')
        mail_port = current_app.config.get('MAIL_PORT')
        mail_username = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')
        mail_use_tls = current_app.config.get('MAIL_USE_TLS')
        mail_use_ssl = current_app.config.get('MAIL_USE_SSL')
        mail_default_sender = current_app.config.get('MAIL_DEFAULT_SENDER')
    
    status['settings'] = {
        'server': mail_server or 'Not configured',
        'port': mail_port or 'Not configured',
        'username': mail_username or 'Not configured',
        'password_set': bool(mail_password),
        'use_tls': mail_use_tls,
        'use_ssl': mail_use_ssl,
        'default_sender': mail_default_sender or 'Not configured'
    }
    
    # Check for configuration issues
    if not mail_server or mail_server == 'localhost':
        status['errors'].append('Mail server not configured or set to localhost')
    
    if not mail_default_sender or mail_default_sender == 'noreply@timetracker.local':
        status['warnings'].append('Default sender email should be configured with a real email address')
    
    if mail_use_tls and mail_use_ssl:
        status['errors'].append('Cannot use both TLS and SSL. Choose one.')
    
    if not mail_username and mail_server not in ['localhost', '127.0.0.1']:
        status['warnings'].append('MAIL_USERNAME not set (may be required for authentication)')
    
    if not mail_password and mail_username:
        status['warnings'].append('MAIL_PASSWORD not set but MAIL_USERNAME is configured')
    
    # Mark as configured if minimum requirements are met
    status['configured'] = bool(mail_server and mail_server != 'localhost' and not status['errors'])
    
    return status


def send_test_email(recipient_email, sender_name='TimeTracker Admin'):
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
        if not recipient_email or '@' not in recipient_email:
            current_app.logger.warning(f"[EMAIL TEST] Invalid recipient email: {recipient_email}")
            return False, 'Invalid recipient email address'
        
        # Check if mail is configured
        mail_server = current_app.config.get('MAIL_SERVER')
        if not mail_server:
            current_app.logger.error("[EMAIL TEST] Mail server not configured")
            return False, 'Mail server not configured. Please set MAIL_SERVER in environment variables.'
        
        # Log current configuration
        current_app.logger.info(f"[EMAIL TEST] Configuration:")
        current_app.logger.info(f"  - Server: {mail_server}:{current_app.config.get('MAIL_PORT')}")
        current_app.logger.info(f"  - TLS: {current_app.config.get('MAIL_USE_TLS')}")
        current_app.logger.info(f"  - SSL: {current_app.config.get('MAIL_USE_SSL')}")
        current_app.logger.info(f"  - Username: {current_app.config.get('MAIL_USERNAME')}")
        current_app.logger.info(f"  - Sender: {current_app.config.get('MAIL_DEFAULT_SENDER')}")
        
        subject = 'TimeTracker Email Test'
        
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
                'email/test_email.html',
                sender_name=sender_name,
                mail_server=current_app.config.get('MAIL_SERVER'),
                mail_port=current_app.config.get('MAIL_PORT'),
                use_tls=current_app.config.get('MAIL_USE_TLS'),
                use_ssl=current_app.config.get('MAIL_USE_SSL')
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
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        # Send synchronously for testing (so we can catch errors)
        current_app.logger.info("[EMAIL TEST] Attempting to send email via SMTP...")
        mail.send(msg)
        current_app.logger.info(f"[EMAIL TEST] ✓ Email sent successfully to {recipient_email}")
        
        return True, f'Test email sent successfully to {recipient_email}'
        
    except Exception as e:
        current_app.logger.error(f"[EMAIL TEST] ✗ Failed to send test email: {type(e).__name__}: {str(e)}")
        current_app.logger.exception("[EMAIL TEST] Full exception trace:")
        return False, f'Failed to send test email: {str(e)}'

