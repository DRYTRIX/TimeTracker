"""
Custom Report Builder Service
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from app import db
from app.models.custom_report import CustomReportConfig
from app.models import TimeEntry, Project, Invoice, Expense, User
from sqlalchemy import func, and_, or_
import logging

logger = logging.getLogger(__name__)


class CustomReportService:
    """Service for building and executing custom reports"""

    def build_report(self, config_id: int, filters: Dict = None) -> Dict[str, Any]:
        """Build a report from a custom configuration"""
        config = CustomReportConfig.query.get_or_404(config_id)

        if not config.is_active:
            return {"error": "Report configuration is inactive"}

        # Get base query based on report type
        if config.report_type == "time":
            return self._build_time_report(config, filters or {})
        elif config.report_type == "project":
            return self._build_project_report(config, filters or {})
        elif config.report_type == "invoice":
            return self._build_invoice_report(config, filters or {})
        elif config.report_type == "expense":
            return self._build_expense_report(config, filters or {})
        elif config.report_type == "combined":
            return self._build_combined_report(config, filters or {})
        else:
            return {"error": f"Unknown report type: {config.report_type}"}

    def _build_time_report(self, config: CustomReportConfig, filters: Dict) -> Dict[str, Any]:
        """Build time entries report"""
        builder_config = config.builder_config or {}
        columns = builder_config.get("columns", [])
        groupings = builder_config.get("groupings", [])

        # Base query
        query = TimeEntry.query.filter(TimeEntry.end_time.isnot(None))

        # Apply filters
        if filters.get("start_date"):
            query = query.filter(TimeEntry.start_time >= filters["start_date"])
        if filters.get("end_date"):
            query = query.filter(TimeEntry.start_time <= filters["end_date"])
        if filters.get("user_id"):
            query = query.filter(TimeEntry.user_id == filters["user_id"])
        if filters.get("project_id"):
            query = query.filter(TimeEntry.project_id == filters["project_id"])

        # Get data
        entries = query.all()

        # Apply groupings
        grouped_data = self._apply_groupings(entries, groupings)

        # Select columns
        formatted_data = self._format_columns(grouped_data, columns)

        return {
            "data": formatted_data,
            "summary": self._calculate_summary(entries),
            "columns": columns,
            "groupings": groupings,
        }

    def _build_project_report(self, config: CustomReportConfig, filters: Dict) -> Dict[str, Any]:
        """Build projects report"""
        query = Project.query.filter_by(status="active")

        if filters.get("client_id"):
            query = query.filter(Project.client_id == filters["client_id"])

        projects = query.all()

        return {"data": [p.to_dict() for p in projects], "summary": {"total_projects": len(projects)}}

    def _build_invoice_report(self, config: CustomReportConfig, filters: Dict) -> Dict[str, Any]:
        """Build invoices report"""
        query = Invoice.query

        if filters.get("start_date"):
            query = query.filter(Invoice.issue_date >= filters["start_date"])
        if filters.get("end_date"):
            query = query.filter(Invoice.issue_date <= filters["end_date"])

        invoices = query.all()

        return {
            "data": [i.to_dict() for i in invoices],
            "summary": {"total_invoices": len(invoices), "total_amount": sum(float(i.total_amount) for i in invoices)},
        }

    def _build_expense_report(self, config: CustomReportConfig, filters: Dict) -> Dict[str, Any]:
        """Build expenses report"""
        query = Expense.query

        if filters.get("start_date"):
            query = query.filter(Expense.date >= filters["start_date"])
        if filters.get("end_date"):
            query = query.filter(Expense.date <= filters["end_date"])

        expenses = query.all()

        return {
            "data": [e.to_dict() for e in expenses],
            "summary": {"total_expenses": len(expenses), "total_amount": sum(float(e.amount) for e in expenses)},
        }

    def _build_combined_report(self, config: CustomReportConfig, filters: Dict) -> Dict[str, Any]:
        """Build combined report with multiple data sources"""
        time_report = self._build_time_report(config, filters)
        invoice_report = self._build_invoice_report(config, filters)
        expense_report = self._build_expense_report(config, filters)

        return {"time": time_report, "invoices": invoice_report, "expenses": expense_report}

    def _apply_groupings(self, entries: List, groupings: List[str]) -> Dict:
        """Apply grouping to entries"""
        if not groupings:
            return {"ungrouped": entries}

        grouped = {}
        for entry in entries:
            key_parts = []
            for group_by in groupings:
                if group_by == "project":
                    key_parts.append(str(entry.project_id))
                elif group_by == "user":
                    key_parts.append(str(entry.user_id))
                elif group_by == "date":
                    key_parts.append(entry.start_time.strftime("%Y-%m-%d") if entry.start_time else "")

            key = "|".join(key_parts) if key_parts else "ungrouped"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(entry)

        return grouped

    def _format_columns(self, data: Dict, columns: List[str]) -> List[Dict]:
        """Format data with selected columns"""
        formatted = []

        if isinstance(data, dict):
            for group_key, entries in data.items():
                for entry in entries:
                    row = {}
                    for col in columns:
                        if hasattr(entry, col):
                            row[col] = getattr(entry, col)
                        elif col == "project_name" and entry.project:
                            row[col] = entry.project.name
                        elif col == "user_name" and entry.user:
                            row[col] = entry.user.display_name
                    formatted.append(row)
        else:
            for entry in data:
                row = {}
                for col in columns:
                    if hasattr(entry, col):
                        row[col] = getattr(entry, col)
                formatted.append(row)

        return formatted

    def _calculate_summary(self, entries: List[TimeEntry]) -> Dict:
        """Calculate summary statistics"""
        total_hours = sum(e.duration_hours for e in entries if e.end_time)
        billable_hours = sum(e.duration_hours for e in entries if e.billable and e.end_time)

        return {
            "total_entries": len(entries),
            "total_hours": round(total_hours, 2),
            "billable_hours": round(billable_hours, 2),
            "non_billable_hours": round(total_hours - billable_hours, 2),
        }
