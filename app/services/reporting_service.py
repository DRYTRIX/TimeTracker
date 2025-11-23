"""
Service for reporting and analytics business logic.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.repositories import TimeEntryRepository, ProjectRepository, InvoiceRepository, ExpenseRepository
from app.models import TimeEntry, Project, Invoice, Expense


class ReportingService:
    """Service for reporting operations"""
    
    def __init__(self):
        self.time_entry_repo = TimeEntryRepository()
        self.project_repo = ProjectRepository()
        self.invoice_repo = InvoiceRepository()
        self.expense_repo = ExpenseRepository()
    
    def get_time_summary(
        self,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        billable_only: bool = False
    ) -> Dict[str, Any]:
        """
        Get time tracking summary.
        
        Returns:
            dict with total hours, billable hours, entries count, etc.
        """
        if not start_date:
            start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()
        
        # Get total duration
        total_seconds = self.time_entry_repo.get_total_duration(
            user_id=user_id,
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            billable_only=billable_only
        )
        
        total_hours = total_seconds / 3600
        
        # Get billable duration
        billable_seconds = self.time_entry_repo.get_total_duration(
            user_id=user_id,
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            billable_only=True
        )
        billable_hours = billable_seconds / 3600
        
        # Get entries
        entries = self.time_entry_repo.get_by_date_range(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            project_id=project_id,
            include_relations=False
        )
        
        return {
            'total_hours': round(total_hours, 2),
            'billable_hours': round(billable_hours, 2),
            'non_billable_hours': round(total_hours - billable_hours, 2),
            'total_entries': len(entries),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
    
    def get_project_summary(
        self,
        project_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get project summary with time, expenses, and invoices.
        
        Returns:
            dict with project statistics
        """
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return {'error': 'Project not found'}
        
        # Get time summary
        time_summary = self.get_time_summary(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get expenses
        expenses = self.expense_repo.get_by_project(
            project_id=project_id,
            start_date=start_date.date() if start_date else None,
            end_date=end_date.date() if end_date else None
        )
        total_expenses = sum(exp.amount for exp in expenses)
        
        # Get invoices
        invoices = self.invoice_repo.get_by_project(project_id)
        total_invoiced = sum(inv.total_amount for inv in invoices)
        
        # Calculate revenue
        billable_hours = time_summary['billable_hours']
        hourly_rate = project.hourly_rate or Decimal('0')
        potential_revenue = float(billable_hours * hourly_rate)
        
        return {
            'project_id': project_id,
            'project_name': project.name,
            'time': time_summary,
            'expenses': {
                'total': float(total_expenses),
                'count': len(expenses),
                'billable': sum(exp.amount for exp in expenses if exp.billable)
            },
            'invoices': {
                'total': float(total_invoiced),
                'count': len(invoices),
                'paid': sum(inv.amount_paid or 0 for inv in invoices)
            },
            'revenue': {
                'potential': potential_revenue,
                'invoiced': float(total_invoiced),
                'paid': sum(float(inv.amount_paid or 0) for inv in invoices)
            }
        }
    
    def get_user_productivity(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get user productivity metrics.
        
        Returns:
            dict with productivity statistics
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        # Get time summary
        time_summary = self.get_time_summary(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get entries by project
        entries = self.time_entry_repo.get_by_date_range(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            include_relations=True
        )
        
        # Group by project
        project_hours = {}
        for entry in entries:
            project_id = entry.project_id
            hours = (entry.duration_seconds or 0) / 3600
            if project_id not in project_hours:
                project_hours[project_id] = {
                    'project_id': project_id,
                    'project_name': entry.project.name if entry.project else 'Unknown',
                    'hours': 0,
                    'entries': 0
                }
            project_hours[project_id]['hours'] += hours
            project_hours[project_id]['entries'] += 1
        
        return {
            'user_id': user_id,
            'time_summary': time_summary,
            'projects': list(project_hours.values()),
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': (end_date - start_date).days
            }
        }

