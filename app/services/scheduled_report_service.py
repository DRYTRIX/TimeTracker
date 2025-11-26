"""
Service for scheduled report generation and email delivery.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models import ReportEmailSchedule, SavedReportView, User
from app.services.reporting_service import ReportingService
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
        timezone: Optional[str] = None
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
                return {
                    'success': False,
                    'message': 'Saved report view not found.'
                }
            
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
                created_by=created_by
            )
            
            db.session.add(schedule)
            if not db.session.commit():
                return {
                    'success': False,
                    'message': 'Could not create schedule due to a database error.'
                }
            
            return {
                'success': True,
                'message': 'Scheduled report created successfully.',
                'schedule': schedule
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating scheduled report: {e}")
            return {
                'success': False,
                'message': f'Error creating schedule: {str(e)}'
            }
    
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
                return {
                    'success': False,
                    'message': 'Schedule not found or inactive.'
                }
            
            saved_view = SavedReportView.query.get(schedule.saved_view_id)
            if not saved_view:
                return {
                    'success': False,
                    'message': 'Saved report view not found.'
                }
            
            # Parse report configuration
            try:
                config = json.loads(saved_view.config_json) if isinstance(saved_view.config_json, str) else saved_view.config_json
            except:
                config = {}
            
            # Generate report data based on config
            report_data = self._generate_report_data(saved_view, config)
            
            # Send email to recipients
            recipients = [email.strip() for email in schedule.recipients.split(',')]
            sent_count = 0
            
            for recipient in recipients:
                try:
                    send_email(
                        to=recipient,
                        subject=f'Scheduled Report: {saved_view.name}',
                        template='email/scheduled_report.html',
                        report_name=saved_view.name,
                        report_data=report_data,
                        generated_at=now_in_app_timezone()
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Error sending report email to {recipient}: {e}")
            
            # Update schedule
            schedule.last_run_at = now_in_app_timezone()
            schedule.next_run_at = self._calculate_next_run(
                schedule.cadence,
                schedule.cron,
                schedule.timezone
            )
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Report sent to {sent_count} recipients.',
                'sent_count': sent_count
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error generating and sending report: {e}")
            return {
                'success': False,
                'message': f'Error generating report: {str(e)}'
            }
    
    def _generate_report_data(
        self,
        saved_view: SavedReportView,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate report data based on saved view configuration.
        
        Returns:
            dict with report data
        """
        # Extract filters from config
        start_date = config.get('start_date')
        end_date = config.get('end_date')
        project_id = config.get('project_id')
        user_id = config.get('user_id')
        
        # Convert date strings to datetime if needed
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date)
        
        # Generate appropriate report based on scope
        scope = saved_view.scope
        
        if scope == 'time':
            return self.reporting_service.get_time_summary(
                user_id=user_id,
                project_id=project_id,
                start_date=start_date,
                end_date=end_date
            )
        elif scope == 'project':
            return self.reporting_service.get_project_summary(
                project_id=project_id,
                start_date=start_date,
                end_date=end_date
            )
        elif scope == 'invoice':
            # Would need invoice service
            return {'message': 'Invoice reports not yet implemented'}
        else:
            return {'message': 'Unknown report scope'}
    
    def _calculate_next_run(
        self,
        cadence: str,
        cron: Optional[str],
        timezone: Optional[str]
    ) -> datetime:
        """
        Calculate next run time for a schedule.
        
        Returns:
            datetime for next run
        """
        now = now_in_app_timezone()
        
        if cadence == 'daily':
            # Next day at 8 AM
            next_run = now + timedelta(days=1)
            return next_run.replace(hour=8, minute=0, second=0, microsecond=0)
        elif cadence == 'weekly':
            # Next Monday at 8 AM
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            next_run = now + timedelta(days=days_until_monday)
            return next_run.replace(hour=8, minute=0, second=0, microsecond=0)
        elif cadence == 'monthly':
            # First day of next month at 8 AM
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1, hour=8, minute=0, second=0, microsecond=0)
            else:
                next_run = now.replace(month=now.month + 1, day=1, hour=8, minute=0, second=0, microsecond=0)
            return next_run
        elif cadence == 'custom-cron' and cron:
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
    
    def list_schedules(
        self,
        user_id: Optional[int] = None,
        active_only: bool = True
    ) -> List[ReportEmailSchedule]:
        """List scheduled reports"""
        query = ReportEmailSchedule.query
        if user_id:
            query = query.filter_by(created_by=user_id)
        if active_only:
            query = query.filter_by(active=True)
        return query.order_by(ReportEmailSchedule.next_run_at.asc()).all()
    
    def update_schedule(
        self,
        schedule_id: int,
        user_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Update a scheduled report"""
        try:
            schedule = ReportEmailSchedule.query.get(schedule_id)
            if not schedule:
                return {
                    'success': False,
                    'message': 'Schedule not found.'
                }
            
            if schedule.created_by != user_id:
                return {
                    'success': False,
                    'message': 'You do not have permission to edit this schedule.'
                }
            
            if 'recipients' in kwargs:
                schedule.recipients = kwargs['recipients']
            if 'cadence' in kwargs:
                schedule.cadence = kwargs['cadence']
            if 'cron' in kwargs:
                schedule.cron = kwargs['cron']
            if 'timezone' in kwargs:
                schedule.timezone = kwargs['timezone']
            if 'active' in kwargs:
                schedule.active = kwargs['active']
            
            if 'cadence' in kwargs or 'cron' in kwargs or 'timezone' in kwargs:
                schedule.next_run_at = self._calculate_next_run(
                    schedule.cadence,
                    schedule.cron,
                    schedule.timezone
                )
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Schedule updated successfully.',
                'schedule': schedule
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating schedule: {e}")
            return {
                'success': False,
                'message': f'Error updating schedule: {str(e)}'
            }
    
    def delete_schedule(
        self,
        schedule_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """Delete a scheduled report"""
        try:
            schedule = ReportEmailSchedule.query.get(schedule_id)
            if not schedule:
                return {
                    'success': False,
                    'message': 'Schedule not found.'
                }
            
            if schedule.created_by != user_id:
                return {
                    'success': False,
                    'message': 'You do not have permission to delete this schedule.'
                }
            
            db.session.delete(schedule)
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Schedule deleted successfully.'
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting schedule: {e}")
            return {
                'success': False,
                'message': f'Error deleting schedule: {str(e)}'
            }

