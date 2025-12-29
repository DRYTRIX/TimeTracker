"""
Service for scheduled report generation and email delivery.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models import ReportEmailSchedule, SavedReportView, User, SalesmanEmailMapping
from app.services.reporting_service import ReportingService
from app.services.unpaid_hours_service import UnpaidHoursService
from app.utils.email import send_email
from app.utils.timezone import now_in_app_timezone
import logging
import json

logger = logging.getLogger(__name__)


class ScheduledReportService:
    """
    Service for scheduled report operations.
    """

    def __init__(self):
        """Initialize ScheduledReportService"""
        self.reporting_service = ReportingService()

    def create_schedule(
        self,
        saved_view_id: int,
        recipients: str,
        cadence: str,
        created_by: int,
        cron: Optional[str] = None,
        timezone: Optional[str] = None,
        split_by_custom_field: bool = False,
        custom_field_name: Optional[str] = None,
        email_distribution_mode: Optional[str] = None,
        recipient_email_template: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a scheduled report.

        Args:
            saved_view_id: ID of saved report view
            recipients: Comma-separated email addresses
            cadence: 'daily', 'weekly', 'monthly', or 'custom-cron'
            created_by: User ID creating the schedule
            cron: Custom cron expression (if cadence is 'custom-cron')
            timezone: Timezone for scheduling

        Returns:
            dict with 'success', 'message', and 'schedule' keys
        """
        try:
            # Validate saved view exists
            saved_view = SavedReportView.query.get(saved_view_id)
            if not saved_view:
                return {"success": False, "message": "Saved report view not found."}

            # Calculate next run time
            next_run_at = self._calculate_next_run(cadence, cron, timezone)

            schedule = ReportEmailSchedule(
                saved_view_id=saved_view_id,
                recipients=recipients,
                cadence=cadence,
                cron=cron,
                timezone=timezone,
                next_run_at=next_run_at,
                active=True,
                created_by=created_by,
                split_by_salesman=split_by_custom_field,  # Reuse existing field
                salesman_field_name=custom_field_name,  # Reuse existing field
                email_distribution_mode=email_distribution_mode or ("single" if not split_by_custom_field else None),
                recipient_email_template=recipient_email_template,
            )

            db.session.add(schedule)
            if not db.session.commit():
                return {"success": False, "message": "Could not create schedule due to a database error."}

            return {"success": True, "message": "Scheduled report created successfully.", "schedule": schedule}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating scheduled report: {e}")
            return {"success": False, "message": f"Error creating schedule: {str(e)}"}

    def generate_and_send_report(self, schedule_id: int) -> Dict[str, Any]:
        """
        Generate and send a scheduled report.

        This is called by the scheduled task.

        Returns:
            dict with 'success', 'message', and 'sent_count' keys
        """
        try:
            schedule = ReportEmailSchedule.query.get(schedule_id)
            if not schedule or not schedule.active:
                return {"success": False, "message": "Schedule not found or inactive."}

            saved_view = SavedReportView.query.get(schedule.saved_view_id)
            if not saved_view:
                return {"success": False, "message": "Saved report view not found."}

            # Parse report configuration
            try:
                config = (
                    json.loads(saved_view.config_json)
                    if isinstance(saved_view.config_json, str)
                    else saved_view.config_json
                )
            except:
                config = {}

            # Check if we should split by custom field
            # Use iterative_report_generation from saved_view if enabled, otherwise check schedule.split_by_salesman
            if saved_view.iterative_report_generation and saved_view.iterative_custom_field_name:
                # Use iterative report generation from saved view
                return self._generate_and_send_custom_field_reports(
                    schedule, saved_view, config, 
                    custom_field_name=saved_view.iterative_custom_field_name
                )
            elif schedule.split_by_salesman and schedule.salesman_field_name:
                # Use legacy split_by_salesman from schedule
                return self._generate_and_send_custom_field_reports(
                    schedule, saved_view, config,
                    custom_field_name=schedule.salesman_field_name
                )
            
            # Validate config before proceeding
            if not isinstance(config, dict):
                logger.error(f"Invalid config for schedule {schedule_id}: config is not a dict")
                return {"success": False, "message": "Invalid report configuration. Please check the saved report view."}
            
            # Generate report data based on config
            report_data = self._generate_report_data(saved_view, config)

            # Send email to recipients
            recipients = [email.strip() for email in schedule.recipients.split(",")]
            sent_count = 0

            # Render email template
            try:
                from flask import render_template
                html_body = render_template(
                    "email/scheduled_report.html",
                    report_name=saved_view.name,
                    report_data=report_data,
                    generated_at=now_in_app_timezone(),
                )
                text_body = f"Scheduled Report: {saved_view.name}\n\nGenerated at: {now_in_app_timezone()}"
            except Exception as e:
                logger.warning(f"Could not render email template, using plain text: {e}")
                html_body = None
                text_body = f"Scheduled Report: {saved_view.name}\n\nGenerated at: {now_in_app_timezone()}\n\nReport data available in HTML version."

            for recipient in recipients:
                try:
                    send_email(
                        subject=f"Scheduled Report: {saved_view.name}",
                        recipients=[recipient],
                        text_body=text_body,
                        html_body=html_body,
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Error sending report email to {recipient}: {e}")

            # Update schedule
            schedule.last_run_at = now_in_app_timezone()
            schedule.next_run_at = self._calculate_next_run(schedule.cadence, schedule.cron, schedule.timezone)

            db.session.commit()

            return {"success": True, "message": f"Report sent to {sent_count} recipients.", "sent_count": sent_count}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error generating and sending report: {e}")
            return {"success": False, "message": f"Error generating report: {str(e)}"}

    def _generate_report_data(self, saved_view: SavedReportView, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate report data based on saved view configuration.

        Returns:
            dict with report data
        """
        # Extract filters from config
        start_date = config.get("start_date")
        end_date = config.get("end_date")
        project_id = config.get("project_id")
        user_id = config.get("user_id")

        # Convert date strings to datetime if needed
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date)

        # Generate appropriate report based on scope
        scope = saved_view.scope

        if scope == "time":
            return self.reporting_service.get_time_summary(
                user_id=user_id, project_id=project_id, start_date=start_date, end_date=end_date
            )
        elif scope == "project":
            return self.reporting_service.get_project_summary(
                project_id=project_id, start_date=start_date, end_date=end_date
            )
        elif scope == "invoice":
            # Would need invoice service
            return {"message": "Invoice reports not yet implemented"}
        else:
            return {"message": "Unknown report scope"}

    def _calculate_next_run(self, cadence: str, cron: Optional[str], timezone: Optional[str]) -> datetime:
        """
        Calculate next run time for a schedule.

        Returns:
            datetime for next run
        """
        now = now_in_app_timezone()

        if cadence == "daily":
            # Next day at 8 AM
            next_run = now + timedelta(days=1)
            return next_run.replace(hour=8, minute=0, second=0, microsecond=0)
        elif cadence == "weekly":
            # Next Monday at 8 AM
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            next_run = now + timedelta(days=days_until_monday)
            return next_run.replace(hour=8, minute=0, second=0, microsecond=0)
        elif cadence == "monthly":
            # First day of next month at 8 AM
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1, hour=8, minute=0, second=0, microsecond=0)
            else:
                next_run = now.replace(month=now.month + 1, day=1, hour=8, minute=0, second=0, microsecond=0)
            return next_run
        elif cadence == "custom-cron" and cron:
            # For custom cron, we'd need a cron parser
            # For now, return next day
            next_run = now + timedelta(days=1)
            return next_run.replace(hour=8, minute=0, second=0, microsecond=0)
        else:
            # Default: next day
            next_run = now + timedelta(days=1)
            return next_run.replace(hour=8, minute=0, second=0, microsecond=0)

    def get_schedule(self, schedule_id: int) -> Optional[ReportEmailSchedule]:
        """Get a schedule by ID"""
        return ReportEmailSchedule.query.get(schedule_id)

    def list_schedules(self, user_id: Optional[int] = None, active_only: bool = True) -> List[ReportEmailSchedule]:
        """List scheduled reports"""
        from sqlalchemy.orm import joinedload
        query = ReportEmailSchedule.query.options(joinedload(ReportEmailSchedule.saved_view))
        if user_id:
            query = query.filter_by(created_by=user_id)
        if active_only:
            query = query.filter_by(active=True)
        return query.order_by(ReportEmailSchedule.next_run_at.asc()).all()

    def update_schedule(self, schedule_id: int, user_id: int, **kwargs) -> Dict[str, Any]:
        """Update a scheduled report"""
        try:
            schedule = ReportEmailSchedule.query.get(schedule_id)
            if not schedule:
                return {"success": False, "message": "Schedule not found."}

            if schedule.created_by != user_id:
                return {"success": False, "message": "You do not have permission to edit this schedule."}

            if "recipients" in kwargs:
                schedule.recipients = kwargs["recipients"]
            if "cadence" in kwargs:
                schedule.cadence = kwargs["cadence"]
            if "cron" in kwargs:
                schedule.cron = kwargs["cron"]
            if "timezone" in kwargs:
                schedule.timezone = kwargs["timezone"]
            if "active" in kwargs:
                schedule.active = kwargs["active"]

            if "cadence" in kwargs or "cron" in kwargs or "timezone" in kwargs:
                schedule.next_run_at = self._calculate_next_run(schedule.cadence, schedule.cron, schedule.timezone)

            db.session.commit()

            return {"success": True, "message": "Schedule updated successfully.", "schedule": schedule}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating schedule: {e}")
            return {"success": False, "message": f"Error updating schedule: {str(e)}"}

    def delete_schedule(self, schedule_id: int, user_id: int) -> Dict[str, Any]:
        """Delete a scheduled report"""
        try:
            schedule = ReportEmailSchedule.query.get(schedule_id)
            if not schedule:
                return {"success": False, "message": "Schedule not found."}

            if schedule.created_by != user_id:
                return {"success": False, "message": "You do not have permission to delete this schedule."}

            db.session.delete(schedule)
            db.session.commit()

            return {"success": True, "message": "Schedule deleted successfully."}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting schedule: {e}")
            return {"success": False, "message": f"Error deleting schedule: {str(e)}"}

    def _generate_and_send_custom_field_reports(
        self, schedule: ReportEmailSchedule, saved_view: SavedReportView, config: Dict[str, Any],
        custom_field_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate and send reports split by custom field value.
        
        This generates individual reports for each unique value of the specified
        custom field and sends them to the configured recipients.
        
        Args:
            schedule: ReportEmailSchedule object
            saved_view: SavedReportView object
            config: Report configuration dict
            custom_field_name: Custom field name to iterate over (if None, uses schedule.salesman_field_name or "salesman")
        
        Returns:
            dict with 'success', 'message', and 'sent_count' keys
        """
        try:
            from datetime import timedelta
            from app.models import Client, TimeEntry
            # Import the generate_report_data function from custom_reports module
            import app.routes.custom_reports as custom_reports_module
            generate_report_data = custom_reports_module.generate_report_data
            
            # Get custom field name - use provided parameter, or fall back to schedule or default
            if not custom_field_name:
                custom_field_name = schedule.salesman_field_name or saved_view.iterative_custom_field_name or "salesman"
            
            # Get date range from config or use defaults
            # Config can have filters at top level or nested
            filters = config.get("filters", {}) if isinstance(config.get("filters"), dict) else {}
            if not filters and "start_date" in config:
                # Filters might be at top level
                filters = config
            
            end_date = now_in_app_timezone()
            if filters.get("end_date"):
                end_date_str = filters["end_date"]
                if isinstance(end_date_str, str):
                    try:
                        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                    except ValueError:
                        try:
                            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                        except:
                            logger.warning(f"Could not parse end_date: {end_date_str}, using current time")
                            end_date = now_in_app_timezone()
                else:
                    end_date = end_date_str
            
            # Default to last month if no start date
            start_date = end_date - timedelta(days=30)
            if filters.get("start_date"):
                start_date_str = filters["start_date"]
                if isinstance(start_date_str, str):
                    try:
                        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    except ValueError:
                        try:
                            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                        except:
                            logger.warning(f"Could not parse start_date: {start_date_str}, using default")
                            start_date = end_date - timedelta(days=30)
                else:
                    start_date = start_date_str
            
            # Get all unique values for the custom field from clients that have time entries in the date range
            # First, get all clients with the custom field
            clients = Client.query.filter_by(status="active").all()
            unique_values = set()
            
            # Also check time entries in the date range to get values that actually have data
            time_entries = TimeEntry.query.filter(
                TimeEntry.end_time.isnot(None),
                TimeEntry.start_time >= start_date,
                TimeEntry.start_time <= end_date
            ).all()
            
            # Collect unique values from both clients and time entries
            for client in clients:
                if client.custom_fields and custom_field_name in client.custom_fields:
                    value = client.custom_fields[custom_field_name]
                    if value:
                        unique_values.add(str(value).strip())
            
            # Also check from time entries (in case client was deleted or field changed)
            for entry in time_entries:
                client = None
                if entry.project and entry.project.client:
                    client = entry.project.client
                elif entry.client:
                    client = entry.client
                
                if client and client.custom_fields and custom_field_name in client.custom_fields:
                    value = client.custom_fields[custom_field_name]
                    if value:
                        unique_values.add(str(value).strip())
            
            if not unique_values:
                logger.warning(f"No unique values found for custom field '{custom_field_name}'")
                return {
                    "success": False,
                    "message": f"No unique values found for custom field '{custom_field_name}'",
                    "sent_count": 0,
                }
            
            # Generate a report for each unique value
            recipients = [email.strip() for email in schedule.recipients.split(",")]
            sent_count = 0
            errors = []
            
            for field_value in sorted(unique_values):
                # Create a modified config with the custom field filter
                modified_config = config.copy()
                # Ensure filters dict exists
                if "filters" not in modified_config:
                    modified_config["filters"] = {}
                elif not isinstance(modified_config["filters"], dict):
                    modified_config["filters"] = {}
                modified_config["filters"]["custom_field_filter"] = {custom_field_name: field_value}
                
                # Generate report data with the filter
                report_data = generate_report_data(modified_config, schedule.created_by)
                
                # Render email template
                try:
                    from flask import render_template
                    html_body = render_template(
                        "email/scheduled_report.html",
                        report_name=f"{saved_view.name} ({custom_field_name}={field_value})",
                        report_data=report_data,
                        generated_at=now_in_app_timezone(),
                        custom_field_name=custom_field_name,
                        custom_field_value=field_value,
                    )
                    text_body = f"Scheduled Report: {saved_view.name} - {custom_field_name}={field_value}\n\nGenerated at: {now_in_app_timezone()}"
                except Exception as e:
                    logger.warning(f"Could not render email template, using plain text: {e}")
                    html_body = None
                    text_body = f"Scheduled Report: {saved_view.name} - {custom_field_name}={field_value}\n\nGenerated at: {now_in_app_timezone()}\n\nReport data available in HTML version."
                
                # Determine recipient(s) based on distribution mode
                report_recipients = self._get_recipients_for_field_value(
                    schedule, field_value, recipients
                )
                
                # Send email to determined recipients
                for recipient in report_recipients:
                    try:
                        send_email(
                            subject=f"Scheduled Report: {saved_view.name} - {custom_field_name}={field_value}",
                            recipients=[recipient],
                            text_body=text_body,
                            html_body=html_body,
                        )
                        sent_count += 1
                        logger.info(f"Sent report to {recipient} for {custom_field_name}={field_value}")
                    except Exception as e:
                        error_msg = f"Error sending to {recipient} ({custom_field_name}={field_value}): {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
            
            # Update schedule
            schedule.last_run_at = now_in_app_timezone()
            schedule.next_run_at = self._calculate_next_run(schedule.cadence, schedule.cron, schedule.timezone)
            db.session.commit()
            
            message = f"Reports sent for {len(unique_values)} unique {custom_field_name} values to {len(recipients)} recipient(s)."
            if errors:
                message += f" Errors: {len(errors)}"
            
            return {
                "success": True,
                "message": message,
                "sent_count": sent_count,
                "errors": errors,
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error generating and sending custom field reports: {e}", exc_info=True)
            return {"success": False, "message": f"Error generating reports: {str(e)}"}
    
    def _get_recipients_for_field_value(
        self, schedule: ReportEmailSchedule, field_value: str, default_recipients: List[str]
    ) -> List[str]:
        """
        Get recipient email addresses for a specific custom field value.
        
        Supports three modes:
        - 'mapping': Use SalesmanEmailMapping table
        - 'template': Use recipient_email_template with {value} placeholder
        - 'single': Use default recipients (fallback)
        
        Args:
            schedule: ReportEmailSchedule object
            field_value: The custom field value (e.g., 'MM', 'PB')
            default_recipients: Fallback recipients if mapping/template fails
            
        Returns:
            List of email addresses
        """
        distribution_mode = schedule.email_distribution_mode or "single"
        
        if distribution_mode == "mapping":
            # Use SalesmanEmailMapping
            from app.models import SalesmanEmailMapping
            email = SalesmanEmailMapping.get_email_for_initial(field_value)
            if email:
                return [email]
            else:
                logger.warning(f"No email mapping found for {field_value}, using default recipients")
                return default_recipients
        
        elif distribution_mode == "template":
            # Use email template
            template = schedule.recipient_email_template
            if template and "{value}" in template:
                email = template.replace("{value}", field_value)
                return [email]
            else:
                logger.warning(f"Invalid email template '{template}', using default recipients")
                return default_recipients
        
        else:
            # Single mode: use default recipients
            return default_recipients
