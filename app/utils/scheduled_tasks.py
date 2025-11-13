"""Scheduled background tasks for the application"""

import logging
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models import Invoice, User, TimeEntry, Project, BudgetAlert, RecurringInvoice
from app.utils.email import send_overdue_invoice_notification, send_weekly_summary
from app.utils.budget_forecasting import check_budget_alerts


logger = logging.getLogger(__name__)


def check_overdue_invoices():
    """Check for overdue invoices and send notifications
    
    This task should be run daily to check for invoices that are past their due date
    and send notifications to users who have overdue invoice notifications enabled.
    """
    try:
        logger.info("Checking for overdue invoices...")
        
        # Get all invoices that are overdue and not paid/cancelled
        today = datetime.utcnow().date()
        overdue_invoices = Invoice.query.filter(
            Invoice.due_date < today,
            Invoice.status.in_(['draft', 'sent'])
        ).all()
        
        logger.info(f"Found {len(overdue_invoices)} overdue invoices")
        
        notifications_sent = 0
        for invoice in overdue_invoices:
            # Update invoice status to overdue if it's not already
            if invoice.status != 'overdue':
                invoice.status = 'overdue'
                db.session.commit()
            
            # Get users to notify (creator and admins)
            users_to_notify = set()
            
            # Add the invoice creator
            if invoice.creator:
                users_to_notify.add(invoice.creator)
            
            # Add all admins
            admins = User.query.filter_by(role='admin', is_active=True).all()
            users_to_notify.update(admins)
            
            # Send notifications
            for user in users_to_notify:
                if user.email and user.email_notifications and user.notification_overdue_invoices:
                    try:
                        send_overdue_invoice_notification(invoice, user)
                        notifications_sent += 1
                        logger.info(f"Sent overdue notification for invoice {invoice.invoice_number} to {user.username}")
                    except Exception as e:
                        logger.error(f"Failed to send notification to {user.username}: {e}")
        
        logger.info(f"Sent {notifications_sent} overdue invoice notifications")
        return notifications_sent
    
    except Exception as e:
        logger.error(f"Error checking overdue invoices: {e}")
        return 0


def send_weekly_summaries():
    """Send weekly time tracking summaries to users
    
    This task should be run weekly (e.g., Sunday evening or Monday morning)
    to send time tracking summaries to users who have opted in.
    """
    try:
        logger.info("Sending weekly summaries...")
        
        # Get users who want weekly summaries
        users = User.query.filter_by(
            is_active=True,
            email_notifications=True,
            notification_weekly_summary=True
        ).all()
        
        logger.info(f"Found {len(users)} users with weekly summaries enabled")
        
        # Calculate date range (last 7 days)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)
        
        summaries_sent = 0
        for user in users:
            if not user.email:
                continue
            
            try:
                # Get time entries for this user in the past week
                entries = TimeEntry.query.filter(
                    TimeEntry.user_id == user.id,
                    TimeEntry.start_time >= datetime.combine(start_date, datetime.min.time()),
                    TimeEntry.start_time < datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
                    TimeEntry.end_time.isnot(None)
                ).all()
                
                if not entries:
                    logger.info(f"No entries for {user.username}, skipping")
                    continue
                
                # Calculate hours worked
                hours_worked = sum(e.duration_hours for e in entries)
                
                # Group by project
                projects_map = {}
                for entry in entries:
                    if entry.project:
                        project_name = entry.project.name
                        if project_name not in projects_map:
                            projects_map[project_name] = {'name': project_name, 'hours': 0}
                        projects_map[project_name]['hours'] += entry.duration_hours
                
                projects_data = sorted(projects_map.values(), key=lambda x: x['hours'], reverse=True)
                
                # Send email
                send_weekly_summary(
                    user=user,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                    hours_worked=hours_worked,
                    projects_data=projects_data
                )
                
                summaries_sent += 1
                logger.info(f"Sent weekly summary to {user.username}")
            
            except Exception as e:
                logger.error(f"Failed to send weekly summary to {user.username}: {e}")
        
        logger.info(f"Sent {summaries_sent} weekly summaries")
        return summaries_sent
    
    except Exception as e:
        logger.error(f"Error sending weekly summaries: {e}")
        return 0


def check_project_budget_alerts():
    """Check all active projects for budget alerts
    
    This task should be run periodically (e.g., every 6 hours) to check
    project budgets and create alerts when thresholds are exceeded.
    """
    try:
        logger.info("Checking project budget alerts...")
        
        # Get all active projects with budgets
        projects = Project.query.filter(
            Project.budget_amount.isnot(None),
            Project.status == 'active'
        ).all()
        
        logger.info(f"Found {len(projects)} active projects with budgets")
        
        total_alerts_created = 0
        for project in projects:
            try:
                # Check for budget alerts
                alerts_to_create = check_budget_alerts(project.id)
                
                # Create alerts
                for alert_data in alerts_to_create:
                    alert = BudgetAlert.create_alert(
                        project_id=alert_data['project_id'],
                        alert_type=alert_data['type'],
                        budget_consumed_percent=alert_data['budget_consumed_percent'],
                        budget_amount=alert_data['budget_amount'],
                        consumed_amount=alert_data['consumed_amount']
                    )
                    total_alerts_created += 1
                    logger.info(f"Created {alert_data['type']} alert for project {project.name}")
            
            except Exception as e:
                logger.error(f"Error checking budget alerts for project {project.id}: {e}")
        
        logger.info(f"Created {total_alerts_created} budget alerts")
        return total_alerts_created
    
    except Exception as e:
        logger.error(f"Error checking project budget alerts: {e}")
        return 0


def generate_recurring_invoices():
    """Generate invoices from active recurring invoice templates
    
    This task should be run daily to check for recurring invoices that need to be generated.
    """
    try:
        logger.info("Generating recurring invoices...")
        
        # Get all active recurring invoices that should generate today
        today = datetime.utcnow().date()
        recurring_invoices = RecurringInvoice.query.filter(
            RecurringInvoice.is_active == True,
            RecurringInvoice.next_run_date <= today
        ).all()
        
        logger.info(f"Found {len(recurring_invoices)} recurring invoices to process")
        
        invoices_generated = 0
        emails_sent = 0
        
        for recurring in recurring_invoices:
            try:
                # Check if we've reached the end date
                if recurring.end_date and today > recurring.end_date:
                    logger.info(f"Recurring invoice {recurring.id} has reached end date, deactivating")
                    recurring.is_active = False
                    db.session.commit()
                    continue
                
                # Generate invoice
                invoice = recurring.generate_invoice()
                if invoice:
                    db.session.commit()
                    invoices_generated += 1
                    logger.info(f"Generated invoice {invoice.invoice_number} from recurring template {recurring.name}")
                    
                    # Auto-send if enabled
                    if recurring.auto_send and invoice.client_email:
                        try:
                            from app.utils.email import send_invoice_email
                            send_invoice_email(invoice, invoice.client_email, sender_user=recurring.creator)
                            emails_sent += 1
                            logger.info(f"Auto-sent invoice {invoice.invoice_number} to {invoice.client_email}")
                        except Exception as e:
                            logger.error(f"Failed to auto-send invoice {invoice.invoice_number}: {e}")
                else:
                    logger.warning(f"Failed to generate invoice from recurring template {recurring.id}")
            
            except Exception as e:
                logger.error(f"Error processing recurring invoice {recurring.id}: {e}")
                db.session.rollback()
        
        logger.info(f"Generated {invoices_generated} invoices, sent {emails_sent} emails")
        return invoices_generated
    
    except Exception as e:
        logger.error(f"Error generating recurring invoices: {e}")
        return 0


def register_scheduled_tasks(scheduler):
    """Register all scheduled tasks with APScheduler
    
    Args:
        scheduler: APScheduler instance
    """
    try:
        # Check overdue invoices daily at 9 AM
        scheduler.add_job(
            func=check_overdue_invoices,
            trigger='cron',
            hour=9,
            minute=0,
            id='check_overdue_invoices',
            name='Check for overdue invoices',
            replace_existing=True
        )
        logger.info("Registered overdue invoices check task")
        
        # Send weekly summaries every Monday at 8 AM
        scheduler.add_job(
            func=send_weekly_summaries,
            trigger='cron',
            day_of_week='mon',
            hour=8,
            minute=0,
            id='send_weekly_summaries',
            name='Send weekly time summaries',
            replace_existing=True
        )
        logger.info("Registered weekly summaries task")
        
        # Check budget alerts every 6 hours
        scheduler.add_job(
            func=check_project_budget_alerts,
            trigger='cron',
            hour='*/6',
            minute=0,
            id='check_budget_alerts',
            name='Check project budget alerts',
            replace_existing=True
        )
        logger.info("Registered budget alerts check task")
        
        # Generate recurring invoices daily at 8 AM
        scheduler.add_job(
            func=generate_recurring_invoices,
            trigger='cron',
            hour=8,
            minute=0,
            id='generate_recurring_invoices',
            name='Generate recurring invoices',
            replace_existing=True
        )
        logger.info("Registered recurring invoices generation task")
        
    except Exception as e:
        logger.error(f"Error registering scheduled tasks: {e}")

