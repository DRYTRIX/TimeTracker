"""Scheduled background tasks for the application"""

import logging
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models import Invoice, User, TimeEntry, Project, BudgetAlert, RecurringInvoice, Quote, ReportEmailSchedule
from app.utils.email import send_overdue_invoice_notification, send_weekly_summary, send_quote_expired_notification
from app.utils.budget_forecasting import check_budget_alerts
from app.services.scheduled_report_service import ScheduledReportService


logger = logging.getLogger(__name__)


def check_overdue_invoices():
    """Check for overdue invoices and send notifications
    
    This task should be run daily to check for invoices that are past their due date
    and send notifications to users who have overdue invoice notifications enabled.
    """
    with current_app.app_context():
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
    with current_app.app_context():
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
    with current_app.app_context():
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
    with current_app.app_context():
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


def register_scheduled_tasks(scheduler, app=None):
    """Register all scheduled tasks with APScheduler
    
    Args:
        scheduler: APScheduler instance
        app: Flask app instance (optional, will use current_app if not provided)
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
        
        # Retry failed webhook deliveries every 5 minutes
        # Create a closure that captures the app instance
        if app is None:
            try:
                app = current_app._get_current_object()
            except RuntimeError:
                logger.warning("Could not get app instance for webhook retry task")
                app = None
        
        def retry_failed_webhooks_with_app():
            """Wrapper that uses the captured app instance"""
            app_instance = app
            if app_instance is None:
                try:
                    app_instance = current_app._get_current_object()
                except RuntimeError:
                    logger.error("No app instance available for webhook retry")
                    return
            
            with app_instance.app_context():
                retry_failed_webhooks()
        
        scheduler.add_job(
            func=retry_failed_webhooks_with_app,
            trigger='cron',
            minute='*/5',
            id='retry_failed_webhooks',
            name='Retry failed webhook deliveries',
            replace_existing=True
        )
        logger.info("Registered webhook retry task")
        
        # Check for expiring quotes daily at 9:30 AM
        scheduler.add_job(
            func=check_expiring_quotes,
            trigger='cron',
            hour=9,
            minute=30,
            id='check_expiring_quotes',
            name='Check for expiring quotes',
            replace_existing=True
        )
        logger.info("Registered expiring quotes check task")
        
        # Process scheduled reports every hour
        scheduler.add_job(
            func=process_scheduled_reports,
            trigger='cron',
            minute=0,
            id='process_scheduled_reports',
            name='Process scheduled reports',
            replace_existing=True
        )
        logger.info("Registered scheduled reports task")
    
    except Exception as e:
        logger.error(f"Error registering scheduled tasks: {e}")


def process_scheduled_reports():
    """Process scheduled reports that are due
    
    This task should be run periodically to check for scheduled reports
    that are due and send them via email.
    """
    with current_app.app_context():
        try:
            logger.info("Processing scheduled reports...")
            
            now = datetime.utcnow()
            due_schedules = ReportEmailSchedule.query.filter(
                ReportEmailSchedule.active == True,
                ReportEmailSchedule.next_run_at <= now
            ).all()
            
            logger.info(f"Found {len(due_schedules)} scheduled reports due")
            
            service = ScheduledReportService()
            processed = 0
            
            for schedule in due_schedules:
                try:
                    result = service.generate_and_send_report(schedule.id)
                    if result['success']:
                        processed += 1
                        logger.info(f"Sent scheduled report {schedule.id} to {result['sent_count']} recipients")
                    else:
                        logger.error(f"Error sending scheduled report {schedule.id}: {result['message']}")
                except Exception as e:
                    logger.error(f"Error processing scheduled report {schedule.id}: {e}")
            
            logger.info(f"Processed {processed} scheduled reports")
            return processed
            
        except Exception as e:
            logger.error(f"Error processing scheduled reports: {e}")
            return 0


def retry_failed_webhooks():
    """Retry failed webhook deliveries
    
    This task should be run periodically to retry webhook deliveries
    that have failed and are scheduled for retry.
    
    Note: This function should be called within an app context.
    Use retry_failed_webhooks_with_app() wrapper for scheduled tasks.
    """
    try:
        from app.utils.webhook_service import WebhookService
        retried_count = WebhookService.retry_failed_deliveries(max_deliveries=100)
        if retried_count > 0:
            logger.info(f"Retried {retried_count} failed webhook deliveries")
    except Exception as e:
        logger.error(f"Error retrying failed webhooks: {e}")


def check_expiring_quotes():
    """Check for quotes expiring soon and send reminders
    
    This task should be run daily to check for quotes that are expiring
    within the next 7 days, 3 days, and 1 day, and send reminders.
    """
    with current_app.app_context():
        try:
            from app.utils.timezone import local_now
            from datetime import timedelta
            from app.utils.email import send_quote_expiring_reminder
            
            logger.info("Checking for expiring quotes...")
            
            today = local_now().date()
            seven_days = today + timedelta(days=7)
            
            # Get quotes that are sent and expiring soon
            expiring_quotes = Quote.query.filter(
                Quote.status == 'sent',
                Quote.valid_until.isnot(None),
                Quote.valid_until >= today,
                Quote.valid_until <= seven_days
            ).all()
            
            logger.info(f"Found {len(expiring_quotes)} quotes expiring soon")
            
            notifications_sent = 0
            for quote in expiring_quotes:
                if not quote.valid_until:
                    continue
                
                days_until_expiry = (quote.valid_until - today).days
                
                # Send reminders at 7 days, 3 days, and 1 day before expiration
                if days_until_expiry not in [7, 3, 1]:
                    continue
                
                # Get users to notify (creator and admins)
                users_to_notify = set()
                
                # Add the quote creator
                if quote.creator:
                    users_to_notify.add(quote.creator)
                
                # Add all admins
                admins = User.query.filter_by(role='admin', is_active=True).all()
                users_to_notify.update(admins)
                
                # Send notifications
                for user in users_to_notify:
                    if user.email and user.email_notifications:
                        try:
                            send_quote_expiring_reminder(quote, user, days_until_expiry)
                            notifications_sent += 1
                            logger.info(f"Sent expiration reminder for quote {quote.quote_number} to {user.username} ({days_until_expiry} days remaining)")
                        except Exception as e:
                            logger.error(f"Failed to send reminder to {user.username}: {e}")
            
            logger.info(f"Sent {notifications_sent} quote expiration reminders")
            return notifications_sent
        
        except Exception as e:
            logger.error(f"Error checking expiring quotes: {e}")
            return 0

