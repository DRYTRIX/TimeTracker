"""
Service for data export operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from io import BytesIO
import csv
from app.repositories import TimeEntryRepository, ProjectRepository, InvoiceRepository, ExpenseRepository
from app.models import TimeEntry, Project, Invoice, Expense


class ExportService:
    """Service for export operations"""

    def __init__(self):
        self.time_entry_repo = TimeEntryRepository()
        self.project_repo = ProjectRepository()
        self.invoice_repo = InvoiceRepository()
        self.expense_repo = ExpenseRepository()

    def export_time_entries_csv(
        self,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> BytesIO:
        """
        Export time entries to CSV.

        Returns:
            BytesIO object with CSV data
        """
        # Get entries
        if start_date and end_date:
            entries = self.time_entry_repo.get_by_date_range(
                start_date=start_date, end_date=end_date, user_id=user_id, project_id=project_id, include_relations=True
            )
        elif project_id:
            entries = self.time_entry_repo.get_by_project(project_id=project_id, include_relations=True)
        elif user_id:
            entries = self.time_entry_repo.get_by_user(user_id=user_id, include_relations=True)
        else:
            entries = []

        # Create CSV
        output = BytesIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "Date",
                "User",
                "Project",
                "Task",
                "Start Time",
                "End Time",
                "Duration (hours)",
                "Notes",
                "Tags",
                "Billable",
                "Source",
            ]
        )

        # Write rows
        for entry in entries:
            duration_hours = (entry.duration_seconds or 0) / 3600
            writer.writerow(
                [
                    entry.start_time.date().isoformat() if entry.start_time else "",
                    entry.user.username if entry.user else "",
                    entry.project.name if entry.project else "",
                    entry.task.name if entry.task else "",
                    entry.start_time.isoformat() if entry.start_time else "",
                    entry.end_time.isoformat() if entry.end_time else "",
                    f"{duration_hours:.2f}",
                    entry.notes or "",
                    entry.tags or "",
                    "Yes" if entry.billable else "No",
                    entry.source or "",
                ]
            )

        output.seek(0)
        return output

    def export_projects_csv(self, status: Optional[str] = None, client_id: Optional[int] = None) -> BytesIO:
        """
        Export projects to CSV.

        Returns:
            BytesIO object with CSV data
        """
        # Get projects
        if status == "active":
            projects = self.project_repo.get_active_projects(client_id=client_id, include_relations=True)
        else:
            projects = (
                self.project_repo.get_all()
                if not client_id
                else self.project_repo.get_by_client(client_id, status=status, include_relations=True)
            )

        # Create CSV
        output = BytesIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            ["Name", "Client", "Status", "Billable", "Hourly Rate", "Budget", "Estimated Hours", "Created", "Updated"]
        )

        # Write rows
        for project in projects:
            writer.writerow(
                [
                    project.name,
                    # Project.client is a string property; relationship is Project.client_obj
                    (project.client_obj.name if getattr(project, "client_obj", None) else project.client) if project else "",
                    project.status,
                    "Yes" if project.billable else "No",
                    str(project.hourly_rate) if project.hourly_rate else "",
                    str(project.budget_amount) if project.budget_amount else "",
                    str(project.estimated_hours) if project.estimated_hours else "",
                    project.created_at.isoformat() if project.created_at else "",
                    project.updated_at.isoformat() if project.updated_at else "",
                ]
            )

        output.seek(0)
        return output

    def export_invoices_csv(self, status: Optional[str] = None, client_id: Optional[int] = None) -> BytesIO:
        """
        Export invoices to CSV.

        Returns:
            BytesIO object with CSV data
        """
        # Get invoices
        if status:
            invoices = self.invoice_repo.get_by_status(status, include_relations=True)
        elif client_id:
            invoices = self.invoice_repo.get_by_client(client_id, include_relations=True)
        else:
            invoices = self.invoice_repo.get_all()

        # Create CSV
        output = BytesIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "Invoice Number",
                "Client",
                "Project",
                "Issue Date",
                "Due Date",
                "Status",
                "Subtotal",
                "Tax",
                "Total",
                "Amount Paid",
                "Outstanding",
            ]
        )

        # Write rows
        for invoice in invoices:
            outstanding = invoice.total_amount - (invoice.amount_paid or 0)
            writer.writerow(
                [
                    invoice.invoice_number,
                    invoice.client_name,
                    invoice.project.name if invoice.project else "",
                    invoice.issue_date.isoformat() if invoice.issue_date else "",
                    invoice.due_date.isoformat() if invoice.due_date else "",
                    invoice.status,
                    str(invoice.subtotal),
                    str(invoice.tax_amount),
                    str(invoice.total_amount),
                    str(invoice.amount_paid or 0),
                    str(outstanding),
                ]
            )

        output.seek(0)
        return output
