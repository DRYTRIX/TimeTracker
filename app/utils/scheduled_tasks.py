"""Scheduled background tasks for the application"""

import logging
from datetime import datetime, timedelta

from flask import current_app

from app import db
from app.models import (
    BudgetAlert,
    Integration,
    Invoice,
    Project,
    Quote,
    RecurringInvoice,
    ReportEmailSchedule,
    TimeEntry,
    User,
)
from app.services.integration_service import IntegrationService
from app.services.scheduled_report_service import ScheduledReportService
from app.utils.budget_forecasting import check_budget_alerts
from app.utils.email import (
    send_missed_clock_in_email,
    send_overdue_invoice_notification,
    send_quote_expired_notification,
    send_remind_to_log_email,
    send_weekly_summary,
)

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
                Invoice.due_date < today, Invoice.status.in_(["draft", "sent"])
            ).all()

            logger.info(f"Found {len(overdue_invoices)} overdue invoices")

            notifications_sent = 0
            for invoice in overdue_invoices:
                # Update invoice status to overdue if it's not already
                if invoice.status != "overdue":
                    invoice.status = "overdue"
                    db.session.commit()

                # Get users to notify (creator and admins)
                users_to_notify = set()

                # Add the invoice creator
                if invoice.creator:
                    users_to_notify.add(invoice.creator)

                # Add all admins
                admins = User.query.filter_by(role="admin", is_active=True).all()
                users_to_notify.update(admins)

                # Send notifications
                for user in users_to_notify:
                    if user.email and user.email_notifications and user.notification_overdue_invoices:
                        try:
                            send_overdue_invoice_notification(invoice, user)
                            notifications_sent += 1
                            logger.info(
                                f"Sent overdue notification for invoice {invoice.invoice_number} to {user.username}"
                            )
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
                is_active=True, email_notifications=True, notification_weekly_summary=True
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
                        TimeEntry.end_time.isnot(None),
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
                                projects_map[project_name] = {"name": project_name, "hours": 0}
                            projects_map[project_name]["hours"] += entry.duration_hours

                    projects_data = sorted(projects_map.values(), key=lambda x: x["hours"], reverse=True)

                    # Send email
                    send_weekly_summary(
                        user=user,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                        hours_worked=hours_worked,
                        projects_data=projects_data,
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
            projects = Project.query.filter(Project.budget_amount.isnot(None), Project.status == "active").all()

            logger.info(f"Found {len(projects)} active projects with budgets")

            total_alerts_created = 0
            for project in projects:
                try:
                    # Check for budget alerts
                    alerts_to_create = check_budget_alerts(project.id)

                    # Create alerts
                    for alert_data in alerts_to_create:
                        alert = BudgetAlert.create_alert(
                            project_id=alert_data["project_id"],
                            alert_type=alert_data["type"],
                            budget_consumed_percent=alert_data["budget_consumed_percent"],
                            budget_amount=alert_data["budget_amount"],
                            consumed_amount=alert_data["consumed_amount"],
                        )
                        total_alerts_created += 1
                        logger.info(f"Created {alert_data['type']} alert for project {project.name}")
                        try:
                            from app.utils.workflow_bridge import fire_budget_threshold_workflow

                            fire_budget_threshold_workflow(project, alert_data)
                        except Exception as wf_err:
                            logger.debug(f"Workflow budget_threshold trigger skipped: {wf_err}")

                except Exception as e:
                    logger.error(f"Error checking budget alerts for project {project.id}: {e}")

            logger.info(f"Created {total_alerts_created} budget alerts")
            return total_alerts_created

        except Exception as e:
            logger.error(f"Error checking project budget alerts: {e}")
            return 0


def check_task_deadline_approaching():
    """Notify workflow rules for tasks due tomorrow."""
    from datetime import date, timedelta

    from app.models import Task
    from app.utils.workflow_bridge import fire_deadline_approaching_workflow

    with current_app.app_context():
        try:
            target_date = date.today() + timedelta(days=1)
            tasks = Task.query.filter(
                Task.due_date == target_date,
                Task.status.notin_(["done", "cancelled"]),
            ).all()
            for task in tasks:
                user_id = task.assigned_to or task.created_by
                if user_id:
                    fire_deadline_approaching_workflow(task, user_id)
            return len(tasks)
        except Exception as e:
            logger.error(f"Error checking task deadlines: {e}")
            return 0


def generate_recurring_invoices():
    """Generate invoices from active recurring invoice templates

    This task should be run daily to check for recurring invoices that need to be generated.

    Note: This function should be called within an app context.
    Use generate_recurring_invoices_with_app() wrapper for scheduled tasks.
    """
    try:
        logger.info("Generating recurring invoices...")

        # Get all active recurring invoices that should generate today
        today = datetime.utcnow().date()
        recurring_invoices = RecurringInvoice.query.filter(
            RecurringInvoice.is_active == True, RecurringInvoice.next_run_date <= today
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


def send_monthly_unpaid_hours_reports():
    """Send monthly unpaid hours reports split by salesman

    This task runs on the first day of each month and generates
    unpaid hours reports for each salesman based on their client assignments.
    """
    with current_app.app_context():
        try:
            logger.info("Sending monthly unpaid hours reports by salesman...")

            from datetime import datetime, timedelta

            from app.models import SalesmanEmailMapping
            from app.services.unpaid_hours_service import UnpaidHoursService
            from app.utils.email import send_email

            # Get last month's date range
            now = datetime.now()
            if now.month == 1:
                last_month_start = datetime(now.year - 1, 12, 1)
                last_month_end = datetime(now.year, 1, 1) - timedelta(seconds=1)
            else:
                last_month_start = datetime(now.year, now.month - 1, 1)
                last_month_end = datetime(now.year, now.month, 1) - timedelta(seconds=1)

            # Get unpaid hours grouped by salesman
            unpaid_service = UnpaidHoursService()
            salesman_reports = unpaid_service.get_unpaid_hours_by_salesman(
                start_date=last_month_start,
                end_date=last_month_end,
                salesman_field_name="salesman",
            )

            sent_count = 0
            for salesman_initial, report_data in salesman_reports.items():
                if salesman_initial == "_UNASSIGNED_":
                    continue

                # Get email for this salesman
                email = SalesmanEmailMapping.get_email_for_initial(salesman_initial)
                if not email:
                    logger.warning(f"No email mapping for salesman {salesman_initial}, skipping")
                    continue

                # Format report data
                formatted_data = {
                    "salesman_initial": salesman_initial,
                    "total_hours": report_data["total_hours"],
                    "total_entries": report_data["total_entries"],
                    "clients": report_data["clients"],
                    "projects": report_data["projects"],
                    "entries": [
                        {
                            "id": e.id,
                            "date": e.start_time.strftime("%Y-%m-%d") if e.start_time else "",
                            "project": e.project.name if e.project else "",
                            # Project.client is a string property; relationship is Project.client_obj
                            "client": (
                                (
                                    e.project.client_obj.name
                                    if (e.project and getattr(e.project, "client_obj", None))
                                    else (e.project.client if e.project else "")
                                )
                                or (e.client.name if e.client else "Unknown")
                            ),
                            "user": e.user.username if e.user else "",
                            "duration": e.duration_hours,
                            "notes": e.notes or "",
                        }
                        for e in report_data["entries"]
                    ],
                }

                try:
                    send_email(
                        to=email,
                        subject=f"Monthly Unpaid Hours Report - {salesman_initial} ({last_month_start.strftime('%Y-%m-%d')} to {last_month_end.strftime('%Y-%m-%d')})",
                        template="email/unpaid_hours_report.html",
                        salesman_initial=salesman_initial,
                        report_data=formatted_data,
                        start_date=last_month_start.strftime("%Y-%m-%d"),
                        end_date=last_month_end.strftime("%Y-%m-%d"),
                    )
                    sent_count += 1
                    logger.info(f"Sent monthly unpaid hours report to {email} for {salesman_initial}")
                except Exception as e:
                    logger.error(f"Error sending report to {email} ({salesman_initial}): {e}")

            logger.info(f"Sent {sent_count} monthly unpaid hours reports")
            return sent_count

        except Exception as e:
            logger.error(f"Error sending monthly unpaid hours reports: {e}")
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
            trigger="cron",
            hour=9,
            minute=0,
            id="check_overdue_invoices",
            name="Check for overdue invoices",
            replace_existing=True,
        )
        logger.info("Registered overdue invoices check task")

        # Send weekly summaries every Monday at 8 AM
        scheduler.add_job(
            func=send_weekly_summaries,
            trigger="cron",
            day_of_week="mon",
            hour=8,
            minute=0,
            id="send_weekly_summaries",
            name="Send weekly time summaries",
            replace_existing=True,
        )
        logger.info("Registered weekly summaries task")

        # Check budget alerts every 6 hours
        scheduler.add_job(
            func=check_project_budget_alerts,
            trigger="cron",
            hour="*/6",
            minute=0,
            id="check_budget_alerts",
            name="Check project budget alerts",
            replace_existing=True,
        )
        logger.info("Registered budget alerts check task")

        scheduler.add_job(
            func=check_task_deadline_approaching,
            trigger="cron",
            hour=8,
            minute=30,
            id="check_task_deadlines",
            name="Check approaching task deadlines",
            replace_existing=True,
        )
        logger.info("Registered task deadline workflow check")

        # Generate recurring invoices daily at 8 AM
        # Create a closure that captures the app instance
        def generate_recurring_invoices_with_app():
            """Wrapper that uses the captured app instance"""
            app_instance = app
            if app_instance is None:
                try:
                    app_instance = current_app._get_current_object()
                except RuntimeError:
                    logger.error("No app instance available for recurring invoices generation")
                    return

            with app_instance.app_context():
                generate_recurring_invoices()

        scheduler.add_job(
            func=generate_recurring_invoices_with_app,
            trigger="cron",
            hour=8,
            minute=0,
            id="generate_recurring_invoices",
            name="Generate recurring invoices",
            replace_existing=True,
        )
        logger.info("Registered recurring invoices generation task")
        logger.info("Registered recurring invoices generation task")

        # Send monthly unpaid hours reports by salesman (first day of month at 9 AM)
        def send_monthly_unpaid_hours_reports_with_app():
            """Wrapper that uses the captured app instance"""
            app_instance = app
            if app_instance is None:
                try:
                    app_instance = current_app._get_current_object()
                except RuntimeError:
                    logger.error("No app instance available for monthly unpaid hours reports")
                    return
            with app_instance.app_context():
                send_monthly_unpaid_hours_reports()

        scheduler.add_job(
            func=send_monthly_unpaid_hours_reports_with_app,
            trigger="cron",
            day=1,
            hour=9,
            minute=0,
            id="send_monthly_unpaid_hours_reports",
            name="Send monthly unpaid hours reports by salesman",
            replace_existing=True,
        )
        logger.info("Registered monthly unpaid hours reports task")

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
            trigger="cron",
            minute="*/5",
            id="retry_failed_webhooks",
            name="Retry failed webhook deliveries",
            replace_existing=True,
        )
        logger.info("Registered webhook retry task")

        # Check for expiring quotes daily at 9:30 AM
        # Create a closure that captures the app instance
        def check_expiring_quotes_with_app():
            """Wrapper that uses the captured app instance"""
            app_instance = app
            if app_instance is None:
                try:
                    app_instance = current_app._get_current_object()
                except RuntimeError:
                    logger.error("No app instance available for expiring quotes check")
                    return

            with app_instance.app_context():
                check_expiring_quotes()

        scheduler.add_job(
            func=check_expiring_quotes_with_app,
            trigger="cron",
            hour=9,
            minute=30,
            id="check_expiring_quotes",
            name="Check for expiring quotes",
            replace_existing=True,
        )
        logger.info("Registered expiring quotes check task")

        # Sync integrations every hour
        def sync_integrations_with_app():
            """Wrapper that uses the captured app instance"""
            app_instance = app
            if app_instance is None:
                try:
                    app_instance = current_app._get_current_object()
                except RuntimeError:
                    logger.error("No app instance available for integration sync")
                    return

            with app_instance.app_context():
                sync_integrations()

        scheduler.add_job(
            func=sync_integrations_with_app,
            trigger="cron",
            minute=0,  # Every hour at minute 0
            id="sync_integrations",
            name="Sync all active integrations",
            replace_existing=True,
        )
        logger.info("Registered integration sync task")

        # Process scheduled reports every hour
        # Create a closure that captures the app instance
        def process_scheduled_reports_with_app():
            """Wrapper that uses the captured app instance"""
            app_instance = app
            if app_instance is None:
                try:
                    app_instance = current_app._get_current_object()
                except RuntimeError:
                    logger.error("No app instance available for scheduled reports processing")
                    return

            with app_instance.app_context():
                process_scheduled_reports()

        scheduler.add_job(
            func=process_scheduled_reports_with_app,
            trigger="cron",
            minute=0,
            id="process_scheduled_reports",
            name="Process scheduled reports",
            replace_existing=True,
        )
        logger.info("Registered scheduled reports task")

        # Remind to log time (end-of-day reminder) – every hour, check users whose local time matches their reminder time
        def process_remind_to_log_with_app():
            app_instance = app
            if app_instance is None:
                try:
                    app_instance = current_app._get_current_object()
                except RuntimeError:
                    logger.error("No app instance available for remind-to-log processing")
                    return
            with app_instance.app_context():
                process_remind_to_log()

        scheduler.add_job(
            func=process_remind_to_log_with_app,
            trigger="cron",
            minute=0,
            id="process_remind_to_log",
            name="Process remind-to-log notifications",
            replace_existing=True,
        )
        logger.info("Registered remind-to-log task")

        def process_missed_clock_in_with_app():
            app_instance = app
            if app_instance is None:
                try:
                    app_instance = current_app._get_current_object()
                except RuntimeError:
                    logger.error("No app instance available for missed clock-in processing")
                    return
            with app_instance.app_context():
                process_missed_clock_in()

        scheduler.add_job(
            func=process_missed_clock_in_with_app,
            trigger="cron",
            minute=0,
            id="process_missed_clock_in",
            name="Process missed clock-in email reminders",
            replace_existing=True,
        )
        logger.info("Registered missed clock-in email task")

        # Smart reminder browser push notifications – every 15 minutes
        def send_smart_reminder_push_with_app():
            app_instance = app
            if app_instance is None:
                try:
                    app_instance = current_app._get_current_object()
                except RuntimeError:
                    logger.error("No app instance available for smart reminder push")
                    return
            with app_instance.app_context():
                try:
                    send_smart_reminder_push_notifications()
                except Exception as e:
                    logger.warning("Smart reminder push job failed: %s", e)

        scheduler.add_job(
            func=send_smart_reminder_push_with_app,
            trigger="interval",
            minutes=15,
            id="smart_reminder_push",
            name="Send smart reminder browser push notifications",
            replace_existing=True,
        )
        logger.info("Registered smart reminder push task")

        def check_working_time_limits_with_app():
            app_instance = app
            if app_instance is None:
                try:
                    app_instance = current_app._get_current_object()
                except RuntimeError:
                    logger.error("No app instance available for working time limits check")
                    return
            with app_instance.app_context():
                check_working_time_limits()

        scheduler.add_job(
            func=check_working_time_limits_with_app,
            trigger="interval",
            minutes=15,
            id="check_working_time_limits",
            name="Check working time limits and auto-close stale workdays",
            replace_existing=True,
        )
        logger.info("Registered working time limits check task")

        # Base telemetry heartbeat (daily) – always-on minimal install footprint
        def send_base_telemetry_heartbeat_with_app():
            app_instance = app
            if app_instance is None:
                try:
                    app_instance = current_app._get_current_object()
                except RuntimeError:
                    return
            with app_instance.app_context():
                try:
                    from app.telemetry.service import send_base_heartbeat

                    send_base_heartbeat()
                except Exception:
                    pass

        scheduler.add_job(
            func=send_base_telemetry_heartbeat_with_app,
            trigger="cron",
            hour=3,
            minute=0,
            id="send_base_telemetry_heartbeat",
            name="Base telemetry heartbeat",
            replace_existing=True,
        )
        logger.info("Registered base telemetry heartbeat task")

        # --- New opt-in connectors (GitHub PAT, Google Calendar OAuth, Slack bot) ---
        # Sync Google Calendar for all active users every 30 minutes.
        def sync_google_calendar_for_all_users_with_app():
            app_instance = app
            if app_instance is None:
                try:
                    app_instance = current_app._get_current_object()
                except RuntimeError:
                    logger.error("No app instance available for Google Calendar connector sync")
                    return
            with app_instance.app_context():
                sync_google_calendar_for_all_users()

        scheduler.add_job(
            func=sync_google_calendar_for_all_users_with_app,
            trigger="interval",
            minutes=30,
            id="sync_google_calendar_connector",
            name="Sync Google Calendar (new connector) for all active users",
            replace_existing=True,
        )
        logger.info("Registered Google Calendar connector sync task")

        # Slack daily summary dispatcher — runs every 30 minutes, checks each
        # active Slack integration whose daily_summary_time matches the window.
        def post_slack_daily_summaries_with_app():
            app_instance = app
            if app_instance is None:
                try:
                    app_instance = current_app._get_current_object()
                except RuntimeError:
                    logger.error("No app instance available for Slack daily summaries")
                    return
            with app_instance.app_context():
                post_slack_daily_summaries()

        scheduler.add_job(
            func=post_slack_daily_summaries_with_app,
            trigger="interval",
            minutes=30,
            id="post_slack_daily_summaries",
            name="Post Slack daily summaries for active Slack integrations",
            replace_existing=True,
        )
        logger.info("Registered Slack daily summary task")

        try:
            from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

            from app.telemetry.otel_setup import record_background_job_outcome

            def _otel_apscheduler_listener(event):
                try:
                    if event.code == EVENT_JOB_ERROR:
                        record_background_job_outcome(event.job_id, False)
                    elif event.code == EVENT_JOB_EXECUTED:
                        record_background_job_outcome(event.job_id, True)
                except Exception:
                    pass

            scheduler.add_listener(_otel_apscheduler_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
            logger.info("Registered OpenTelemetry APScheduler listener")
        except Exception as listener_err:
            logger.debug("OpenTelemetry APScheduler listener not registered: %s", listener_err)

    except Exception as e:
        logger.error(f"Error registering scheduled tasks: {e}")


def send_smart_reminder_push_notifications():
    """Send browser push notifications for actionable smart reminders.

    For every active user that has smart notifications enabled AND has opted into
    one of the new reminder kinds, ask :class:`NotificationService` what they would
    see right now and push any actionable ``info``/``warning`` entries to their
    registered push subscriptions. Degrades silently if the push_notifications
    blueprint is absent or pywebpush is not installed.
    """
    with current_app.app_context():
        try:
            from app.routes import push_notifications as _push_bp_mod  # noqa: F401
        except Exception:
            logger.debug("push_notifications blueprint not available; skipping smart reminder push job")
            return 0

        try:
            from app.models import PushSubscription
        except Exception:
            logger.debug("PushSubscription model not available; skipping smart reminder push job")
            return 0

        try:
            from app.services.notification_service import NotificationService
        except Exception:
            logger.debug("NotificationService not available; skipping smart reminder push job")
            return 0

        try:
            users = User.query.filter(
                User.is_active == True,
                User.smart_notifications_enabled == True,
                db.or_(
                    User.smart_notify_break_reminder == True,
                    User.smart_notify_end_of_day == True,
                    User.smart_notify_no_tracking == True,
                    User.smart_notify_missed_clock_in == True,
                ),
            ).all()
        except Exception as e:
            logger.warning("Could not query users for smart reminder push: %s", e)
            return 0

        if not users:
            return 0

        sent = 0
        for user in users:
            try:
                payload = NotificationService.build_for_user(user)
                notifications = (payload or {}).get("notifications") or []
                if not notifications:
                    continue
                subscriptions = PushSubscription.get_user_subscriptions(user.id)
                if not subscriptions:
                    logger.debug("User %s has no push subscriptions; skipping", user.username)
                    continue
                for note in notifications:
                    ntype = (note.get("type") or "").lower()
                    if ntype not in ("warning", "info"):
                        continue
                    _delivered = _deliver_push_to_subscriptions(user, subscriptions, note)
                    if _delivered:
                        sent += _delivered
                logger.debug("Smart reminder push processed for %s", user.username)
            except Exception as e:
                logger.warning("Smart reminder push failed for user %s: %s", getattr(user, "username", user.id), e)
        return sent


def _deliver_push_to_subscriptions(user, subscriptions, note) -> int:
    """Send a single notification to all of the user's push subscriptions.

    Uses pywebpush when available and VAPID keys are configured; otherwise logs at
    debug and reports zero deliveries so the scheduler job can keep going.
    """
    try:
        from pywebpush import WebPushException, webpush  # type: ignore
    except Exception:
        logger.debug("pywebpush not installed; smart reminder push skipped for %s", user.username)
        return 0

    cfg = current_app.config
    vapid_private = (cfg.get("VAPID_PRIVATE_KEY") or "").strip()
    vapid_public = (cfg.get("VAPID_PUBLIC_KEY") or "").strip()
    vapid_claims_email = (cfg.get("VAPID_CONTACT_EMAIL") or cfg.get("MAIL_DEFAULT_SENDER") or "").strip()
    if not vapid_private or not vapid_public:
        logger.debug("VAPID keys not configured; smart reminder push skipped for %s", user.username)
        return 0

    import json as _json

    body = {
        "kind": note.get("kind"),
        "title": note.get("title") or "TimeTracker",
        "message": note.get("message") or "",
        "type": note.get("type") or "info",
        "action": note.get("action") or None,
    }
    delivered = 0
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={"endpoint": sub.endpoint, "keys": sub.keys or {}},
                data=_json.dumps(body),
                vapid_private_key=vapid_private,
                vapid_claims={
                    "sub": f"mailto:{vapid_claims_email}" if vapid_claims_email else "mailto:noreply@example.invalid"
                },
            )
            try:
                sub.update_last_used()
            except Exception:
                pass
            delivered += 1
        except WebPushException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):
                try:
                    db.session.delete(sub)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
            else:
                logger.warning("Web push failed for %s (endpoint=%s): %s", user.username, sub.endpoint[:60], e)
        except Exception as e:
            logger.warning("Web push failed for %s (endpoint=%s): %s", user.username, sub.endpoint[:60], e)
    return delivered


def process_remind_to_log():
    """Send end-of-day reminder to log time to users who have it enabled and have not logged (or logged very little) today.

    Runs every hour; for each user with notification_remind_to_log and reminder_to_log_time set,
    if current time in user's timezone matches the reminder hour and they have < 0.5h logged today (user's local day), send email.
    """
    from datetime import time as dt_time
    from datetime import timezone as tz_utc

    from app.utils.timezone import get_timezone_for_user, now_in_user_timezone

    try:
        users = User.query.filter(
            User.is_active == True,
            User.email_notifications == True,
            User.notification_remind_to_log == True,
            User.reminder_to_log_time.isnot(None),
            User.reminder_to_log_time != "",
        ).all()
        if not users:
            return 0
        sent = 0
        for user in users:
            try:
                if not user.email:
                    continue
                user_now = now_in_user_timezone(user)
                reminder_time = (user.reminder_to_log_time or "").strip()
                if not reminder_time or ":" not in reminder_time:
                    continue
                parts = reminder_time.split(":", 1)
                try:
                    reminder_hour = int(parts[0])
                    reminder_min = int(parts[1]) if len(parts) > 1 else 0
                except (ValueError, IndexError):
                    continue
                if not (user_now.hour == reminder_hour and user_now.minute < 30):
                    continue
                user_tz = get_timezone_for_user(user)
                user_today = user_now.date()
                start_local = datetime.combine(user_today, dt_time.min).replace(tzinfo=user_tz)
                end_local = start_local + timedelta(days=1)
                start_utc = start_local.astimezone(tz_utc)
                end_utc = end_local.astimezone(tz_utc)
                from sqlalchemy import func

                total_seconds = (
                    db.session.query(func.coalesce(func.sum(TimeEntry.duration_seconds), 0))
                    .filter(
                        TimeEntry.user_id == user.id,
                        TimeEntry.start_time >= start_utc,
                        TimeEntry.start_time < end_utc,
                        TimeEntry.end_time.isnot(None),
                    )
                    .scalar()
                    or 0
                )
                today_hours = total_seconds / 3600.0
                if today_hours >= 0.5:
                    continue
                send_remind_to_log_email(user)
                sent += 1
                logger.info("Sent remind-to-log email to %s", user.username)
            except Exception as e:
                logger.error("Failed to process remind-to-log for user %s: %s", getattr(user, "username", user.id), e)
        return sent
    except Exception as e:
        logger.error("Error in process_remind_to_log: %s", e)
        return 0


def process_missed_clock_in():
    """Email users who enabled missed clock-in reminders and have not started workday today."""
    from app.services.notification_service import (
        _in_time_slot_after,
        has_workday_started_today,
        is_expected_work_day,
        parse_hhmm,
    )
    from app.utils.timezone import now_in_user_timezone

    try:
        users = User.query.filter(
            User.is_active == True,
            User.email_notifications == True,
            User.notification_missed_clock_in == True,
        ).all()
        if not users:
            return 0
        slot_minutes = int(current_app.config.get("SMART_NOTIFY_SCHEDULER_SLOT_MINUTES") or 30)
        default_at = (current_app.config.get("SMART_NOTIFY_MISSED_CLOCK_IN_AT") or "09:30").strip()
        sent = 0
        for user in users:
            try:
                if not user.email:
                    continue
                user_now = now_in_user_timezone(user)
                reminder_t = parse_hhmm(getattr(user, "smart_notify_missed_clock_in_at", None)) or parse_hhmm(
                    default_at
                )
                if not reminder_t:
                    reminder_t = (9, 30)
                if not _in_time_slot_after(user_now, reminder_t[0], reminder_t[1], slot_minutes):
                    continue
                today = user_now.date()
                if not is_expected_work_day(user.id, today):
                    continue
                if has_workday_started_today(user.id, today):
                    continue
                send_missed_clock_in_email(user)
                sent += 1
                logger.info("Sent missed clock-in email to %s", user.username)
            except Exception as e:
                logger.error(
                    "Failed to process missed clock-in for user %s: %s",
                    getattr(user, "username", user.id),
                    e,
                )
        return sent
    except Exception as e:
        logger.error("Error in process_missed_clock_in: %s", e)
        return 0


def check_working_time_limits():
    """Auto-close stale workday sessions and detect daily/weekly hour limit violations."""
    from app.models import Settings, User
    from app.services.workday_session_service import WorkdaySessionService
    from app.services.working_time_limit_service import WorkingTimeLimitService
    from app.utils.email import send_working_time_limit_exceeded_email

    try:
        settings = Settings.get_settings()
        if not getattr(settings, "hour_limits_enabled", True):
            WorkdaySessionService().auto_close_stale_sessions()
            return 0

        closed = WorkdaySessionService().auto_close_stale_sessions()
        if closed:
            logger.info("Auto-closed %d stale workday session(s)", closed)

        limit_service = WorkingTimeLimitService()
        emails_sent = 0
        users = User.query.filter_by(is_active=True).all()
        for user in users:
            if not user.email or not user.email_notifications:
                continue
            new_violations = limit_service.check_user_limits(user)
            if not getattr(settings, "hour_limit_email_enabled", True):
                continue
            for violation in new_violations:
                try:
                    send_working_time_limit_exceeded_email(user, violation)
                    violation.notified_at = datetime.utcnow()
                    db.session.commit()
                    emails_sent += 1
                except Exception as e:
                    logger.error("Failed to send limit email to %s: %s", user.username, e)
                    db.session.rollback()

        if emails_sent:
            logger.info("Sent %d working time limit notification(s)", emails_sent)

        if getattr(settings, "compliance_enabled", False):
            from app.services.attendance_compliance_service import AttendanceComplianceService

            svc = AttendanceComplianceService()
            svc.sync_all_approved_time_off()
            today = datetime.utcnow().date()
            svc.sync_company_holidays(today - timedelta(days=7), today + timedelta(days=365))

        return emails_sent
    except Exception as e:
        logger.error("Error in check_working_time_limits: %s", e)
        return 0


def process_scheduled_reports():
    """Process scheduled reports that are due

    This task should be run periodically to check for scheduled reports
    that are due and send them via email.

    Note: This function should be called within an app context.
    Use process_scheduled_reports_with_app() wrapper for scheduled tasks.
    """
    try:
        logger.info("Processing scheduled reports...")

        now = datetime.utcnow()
        due_schedules = ReportEmailSchedule.query.filter(
            ReportEmailSchedule.active == True, ReportEmailSchedule.next_run_at <= now
        ).all()

        logger.info(f"Found {len(due_schedules)} scheduled reports due")

        service = ScheduledReportService()
        processed = 0

        for schedule in due_schedules:
            try:
                result = service.generate_and_send_report(schedule.id)
                if result["success"]:
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

    Note: This function should be called within an app context.
    Use check_expiring_quotes_with_app() wrapper for scheduled tasks.
    """
    try:
        from datetime import timedelta

        from app.utils.email import send_quote_expiring_reminder
        from app.utils.timezone import local_now

        logger.info("Checking for expiring quotes...")

        today = local_now().date()
        seven_days = today + timedelta(days=7)

        # Get quotes that are sent and expiring soon
        expiring_quotes = Quote.query.filter(
            Quote.status == "sent",
            Quote.valid_until.isnot(None),
            Quote.valid_until >= today,
            Quote.valid_until <= seven_days,
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
            admins = User.query.filter_by(role="admin", is_active=True).all()
            users_to_notify.update(admins)

            # Send notifications
            for user in users_to_notify:
                if user.email and user.email_notifications:
                    try:
                        send_quote_expiring_reminder(quote, user, days_until_expiry)
                        notifications_sent += 1
                        logger.info(
                            f"Sent expiration reminder for quote {quote.quote_number} to {user.username} ({days_until_expiry} days remaining)"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send reminder to {user.username}: {e}")

        logger.info(f"Sent {notifications_sent} quote expiration reminders")
        return notifications_sent

    except Exception as e:
        logger.error(f"Error checking expiring quotes: {e}")
        return 0


def sync_integrations():
    """Sync all active integrations

    This task should be run periodically to sync data from all active integrations.
    It will only sync integrations that have auto_sync enabled in their config.
    """
    try:
        logger.info("Starting integration sync...")

        # Get all active integrations
        active_integrations = Integration.query.filter_by(is_active=True).all()

        logger.info(f"Found {len(active_integrations)} active integrations")

        service = IntegrationService()
        synced_count = 0
        errors = []

        for integration in active_integrations:
            try:
                # Check if auto_sync is enabled (default to True if not set)
                config = integration.config or {}
                auto_sync = config.get("auto_sync", False)

                if not auto_sync:
                    logger.debug(f"Skipping integration {integration.id} ({integration.provider}): auto_sync disabled")
                    continue

                sync_interval = config.get("sync_interval", 60)
                if sync_interval == "manual":
                    logger.debug(f"Skipping integration {integration.id}: manual sync_interval")
                    continue
                if isinstance(sync_interval, str) and sync_interval.isdigit():
                    sync_interval = int(sync_interval)
                if isinstance(sync_interval, (int, float)):
                    last_run = config.get("last_scheduled_sync_at")
                    interval_minutes = int(sync_interval)
                    if last_run:
                        try:
                            last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                            if (
                                datetime.utcnow() - last_dt.replace(tzinfo=None)
                            ).total_seconds() < interval_minutes * 60:
                                logger.debug(f"Skipping integration {integration.id}: sync interval not elapsed")
                                continue
                        except (ValueError, TypeError):
                            pass
                elif sync_interval == "daily" and datetime.utcnow().hour != 2:
                    logger.debug(f"Skipping integration {integration.id}: daily sync not due")
                    continue

                # Get connector
                connector = service.get_connector(integration)
                if not connector:
                    logger.warning(f"Could not get connector for integration {integration.id} ({integration.provider})")
                    continue

                # Perform sync
                logger.info(f"Syncing integration {integration.id} ({integration.provider})...")
                result = connector.sync_data(sync_type="incremental")

                if result.get("success"):
                    synced_count += 1
                    # Update last sync time
                    integration.last_sync_at = datetime.utcnow()
                    integration.last_sync_status = "success"
                    integration.last_error = None
                    cfg = dict(integration.config or {})
                    cfg["last_scheduled_sync_at"] = datetime.utcnow().isoformat()
                    integration.config = cfg
                    logger.info(
                        f"Successfully synced integration {integration.id} ({integration.provider}): {result.get('synced_items', 0)} items"
                    )
                else:
                    errors.append(f"{integration.provider}: {result.get('message', 'Unknown error')}")
                    integration.last_sync_status = "error"
                    integration.last_error = result.get("message", "Unknown error")
                    logger.error(
                        f"Failed to sync integration {integration.id} ({integration.provider}): {result.get('message')}"
                    )

                from app.utils.integration_sync_context import sync_result_item_count

                _n = sync_result_item_count(result)
                service._log_event(
                    integration.id,
                    "sync",
                    bool(result.get("success")),
                    result.get("message"),
                    (
                        {"synced_count": _n, "synced_items": _n, "trigger": "scheduler"}
                        if _n or result.get("success")
                        else {"trigger": "scheduler"}
                    ),
                )

            except Exception as e:
                error_msg = f"Error syncing integration {integration.id} ({integration.provider}): {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
                integration.last_sync_status = "error"
                integration.last_error = str(e)
                try:
                    service._log_event(integration.id, "sync", False, str(e), {"trigger": "scheduler"})
                except Exception as log_err:
                    logger.warning("Could not log integration sync failure: %s", log_err)
                    db.session.commit()

        logger.info(f"Integration sync completed. Synced {synced_count}/{len(active_integrations)} integrations")
        if errors:
            logger.warning(f"Integration sync errors: {', '.join(errors)}")

        return {"synced": synced_count, "total": len(active_integrations), "errors": errors}

    except Exception as e:
        logger.error(f"Error in integration sync task: {e}", exc_info=True)
        return {"synced": 0, "total": 0, "errors": [str(e)]}


# ---------------------------------------------------------------------------
# New opt-in connectors (GitHubConnector, GoogleCalendarConnector,
# SlackConnector). These functions run inside an app context provided by the
# scheduler wrappers above.
# ---------------------------------------------------------------------------
def sync_google_calendar_for_all_users():
    """Sync every active Google Calendar integration created with the new
    :class:`app.integrations.google_calendar_connector.GoogleCalendarConnector`.

    Each user is wrapped in try/except so one failing account does not block
    the rest. Never raises.
    """
    try:
        from app.integrations.google_calendar_connector import GoogleCalendarConnector
    except Exception as exc:
        logger.debug("GoogleCalendarConnector not importable; skipping job: %s", exc)
        return {"ok": False, "synced": 0, "errors": [str(exc)]}

    synced = 0
    errors = []
    for connector in GoogleCalendarConnector.for_any_active():
        integration = connector.integration
        try:
            result = connector.sync()
            if result.get("ok"):
                synced += 1
            else:
                err = result.get("error") or "; ".join(result.get("errors", []) or [])
                errors.append(f"integration {integration.id}: {err}")
                logger.warning("Google Calendar sync skipped for integration %s: %s", integration.id, err)
        except Exception as exc:
            errors.append(f"integration {integration.id}: {exc}")
            logger.warning("Google Calendar sync failed for integration %s: %s", integration.id, exc)
    logger.info("Google Calendar connector sync: %d ok, %d errors", synced, len(errors))
    return {"ok": True, "synced": synced, "errors": errors}


def post_slack_daily_summaries():
    """Post Slack daily summary messages for users whose configured time matches
    the current 30-minute window.

    Runs every 30 minutes; ``daily_summary_time`` is treated as the start of
    the window so e.g. "18:00" matches 18:00..18:29 inclusive.
    """
    try:
        from app.integrations.slack_connector import SlackConnector
    except Exception as exc:
        logger.debug("SlackConnector not importable; skipping job: %s", exc)
        return {"ok": False, "posted": 0}

    try:
        from app.models import User
    except Exception:
        return {"ok": False, "posted": 0}

    from datetime import datetime

    posted = 0
    for connector in SlackConnector.for_any_active():
        cfg = dict(connector.integration.config or {})
        if not cfg.get("daily_summary"):
            continue
        target = (cfg.get("daily_summary_time") or "18:00").strip()
        try:
            hh, mm = target.split(":")
            target_hour = int(hh)
            target_minute = int(mm)
        except (ValueError, AttributeError):
            target_hour, target_minute = 18, 0

        # User-local time would be ideal but we don't always have a TZ. Use
        # the user's preferred timezone if available, else the app timezone.
        try:
            user = User.query.get(connector.integration.user_id) if connector.integration.user_id else None
            if user is not None:
                from app.utils.timezone import now_in_user_timezone

                local_now = now_in_user_timezone(user)
            else:
                from app.utils.timezone import get_timezone_obj

                tz = get_timezone_obj()
                local_now = datetime.now(tz)
        except Exception:
            local_now = datetime.now()

        # Match if we're inside the 30-minute window that starts at target.
        slot = (local_now.hour - target_hour) * 60 + (local_now.minute - target_minute)
        if slot < 0 or slot >= 30:
            continue
        try:
            connector.post_daily_summary(user)
            posted += 1
        except Exception as exc:
            logger.warning(
                "Slack daily summary failed for integration %s: %s",
                connector.integration.id,
                exc,
            )
    logger.info("Slack daily summary dispatcher: posted=%d", posted)
    return {"ok": True, "posted": posted}
