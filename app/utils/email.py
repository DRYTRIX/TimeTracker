"""Email utilities for sending notifications and reports"""

import os
from flask import current_app, render_template, url_for
from flask_mail import Mail, Message
from threading import Thread
from datetime import datetime, timedelta


mail = Mail()


def init_mail(app):
    """Initialize Flask-Mail with the app"""
    # Configure mail settings from environment variables
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'localhost')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@timetracker.local')
    app.config['MAIL_MAX_EMAILS'] = int(os.getenv('MAIL_MAX_EMAILS', 100))
    
    mail.init_app(app)
    return mail


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

