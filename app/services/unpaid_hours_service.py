"""
Service for querying unpaid hours with custom field filtering.

This service provides methods to:
- Query unpaid (unbilled) time entries
- Filter by client custom fields (e.g., salesman)
- Group by salesman for report generation
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import joinedload
from app import db
from app.models import TimeEntry, InvoiceItem, Client, Project


class UnpaidHoursService:
    """Service for unpaid hours queries and reporting"""

    def get_unpaid_time_entries(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        user_id: Optional[int] = None,
        custom_field_filter: Optional[Dict[str, Any]] = None,
    ) -> List[TimeEntry]:
        """
        Get unpaid (unbilled) time entries.
        
        Unpaid means:
        - billable = True
        - paid = False
        - Not referenced in any InvoiceItem.time_entry_ids
        
        Args:
            start_date: Filter entries from this date
            end_date: Filter entries until this date
            project_id: Filter by project
            client_id: Filter by client
            user_id: Filter by user
            custom_field_filter: Dict with field name and value to filter by client custom fields
                               e.g., {"salesman": "MM"} or {"field_name": "value"}
        
        Returns:
            List of TimeEntry objects that are unpaid
        """
        # Start with base query for billable, unpaid entries
        query = TimeEntry.query.filter(
            TimeEntry.billable == True,
            TimeEntry.paid == False,
            TimeEntry.end_time.isnot(None),
        )

        # Date filters
        if start_date:
            query = query.filter(TimeEntry.start_time >= start_date)
        if end_date:
            query = query.filter(TimeEntry.start_time <= end_date)

        # Project/Client/User filters
        if project_id:
            query = query.filter(TimeEntry.project_id == project_id)
        if client_id:
            query = query.filter(TimeEntry.client_id == client_id)
        if user_id:
            query = query.filter(TimeEntry.user_id == user_id)

        # Get all entries first
        all_entries = query.options(joinedload(TimeEntry.project), joinedload(TimeEntry.client)).all()

        # Get all billed time entry IDs from invoice items
        billed_entry_ids = set()
        invoice_items = InvoiceItem.query.filter(InvoiceItem.time_entry_ids.isnot(None)).all()
        for item in invoice_items:
            if item.time_entry_ids:
                try:
                    entry_ids = [int(id_str.strip()) for id_str in item.time_entry_ids.split(",") if id_str.strip()]
                    billed_entry_ids.update(entry_ids)
                except (ValueError, AttributeError):
                    continue

        # Filter out billed entries
        unpaid_entries = [entry for entry in all_entries if entry.id not in billed_entry_ids]

        # Apply custom field filter if provided
        if custom_field_filter:
            unpaid_entries = self._filter_by_custom_fields(unpaid_entries, custom_field_filter)

        return unpaid_entries

    def _filter_by_custom_fields(self, entries: List[TimeEntry], custom_field_filter: Dict[str, Any]) -> List[TimeEntry]:
        """
        Filter entries by client custom fields.
        
        Args:
            entries: List of TimeEntry objects
            custom_field_filter: Dict with field name and value
                               e.g., {"salesman": "MM"}
        
        Returns:
            Filtered list of TimeEntry objects
        """
        if not custom_field_filter:
            return entries

        filtered = []
        for entry in entries:
            # Get client from entry (via project or direct)
            client = None
            if entry.project and entry.project.client:
                client = entry.project.client
            elif entry.client:
                client = entry.client

            if not client or not client.custom_fields:
                continue

            # Check if any custom field matches
            matches = True
            for field_name, field_value in custom_field_filter.items():
                client_value = client.custom_fields.get(field_name)
                # Case-insensitive comparison
                if str(client_value).upper().strip() != str(field_value).upper().strip():
                    matches = False
                    break

            if matches:
                filtered.append(entry)

        return filtered

    def get_unpaid_hours_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        custom_field_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get summary of unpaid hours.
        
        Returns:
            Dict with total_hours, total_entries, and breakdown by client/project
        """
        entries = self.get_unpaid_time_entries(
            start_date=start_date,
            end_date=end_date,
            custom_field_filter=custom_field_filter,
        )

        total_hours = sum(entry.duration_hours or 0 for entry in entries)
        
        # Group by client
        by_client = {}
        by_project = {}
        
        for entry in entries:
            client = None
            if entry.project and entry.project.client:
                client = entry.project.client
            elif entry.client:
                client = entry.client

            if client:
                client_name = client.name
                if client_name not in by_client:
                    by_client[client_name] = {"hours": 0, "entries": []}
                by_client[client_name]["hours"] += entry.duration_hours or 0
                by_client[client_name]["entries"].append(entry)

            if entry.project:
                project_name = entry.project.name
                if project_name not in by_project:
                    by_project[project_name] = {"hours": 0, "entries": []}
                by_project[project_name]["hours"] += entry.duration_hours or 0
                by_project[project_name]["entries"].append(entry)

        return {
            "total_hours": round(total_hours, 2),
            "total_entries": len(entries),
            "by_client": by_client,
            "by_project": by_project,
        }

    def group_by_salesman(
        self,
        entries: List[TimeEntry],
        salesman_field_name: str = "salesman",
    ) -> Dict[str, List[TimeEntry]]:
        """
        Group unpaid hours by salesman initial from client custom fields.
        
        Args:
            entries: List of TimeEntry objects
            salesman_field_name: Name of the custom field containing salesman info
        
        Returns:
            Dict mapping salesman initial to list of TimeEntry objects
        """
        grouped = {}
        unassigned = []

        for entry in entries:
            # Get client from entry
            client = None
            if entry.project and entry.project.client:
                client = entry.project.client
            elif entry.client:
                client = entry.client

            if not client or not client.custom_fields:
                unassigned.append(entry)
                continue

            salesman_value = client.custom_fields.get(salesman_field_name)
            if not salesman_value:
                unassigned.append(entry)
                continue

            # Normalize salesman initial (uppercase, strip)
            salesman_initial = str(salesman_value).upper().strip()
            
            if salesman_initial not in grouped:
                grouped[salesman_initial] = []
            
            grouped[salesman_initial].append(entry)

        # Add unassigned entries to a special key
        if unassigned:
            grouped["_UNASSIGNED_"] = unassigned

        return grouped

    def get_unpaid_hours_by_salesman(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        salesman_field_name: str = "salesman",
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get unpaid hours grouped by salesman.
        
        Returns:
            Dict mapping salesman initial to summary dict with:
            - entries: List of TimeEntry objects
            - total_hours: Total hours for this salesman
            - clients: List of unique clients
            - projects: List of unique projects
        """
        entries = self.get_unpaid_time_entries(
            start_date=start_date,
            end_date=end_date,
        )

        grouped_entries = self.group_by_salesman(entries, salesman_field_name)

        result = {}
        for salesman_initial, salesman_entries in grouped_entries.items():
            total_hours = sum(entry.duration_hours or 0 for entry in salesman_entries)
            
            # Get unique clients and projects
            clients = set()
            projects = set()
            for entry in salesman_entries:
                if entry.project and entry.project.client:
                    clients.add(entry.project.client.name)
                elif entry.client:
                    clients.add(entry.client.name)
                if entry.project:
                    projects.add(entry.project.name)

            result[salesman_initial] = {
                "entries": salesman_entries,
                "total_hours": round(total_hours, 2),
                "total_entries": len(salesman_entries),
                "clients": sorted(list(clients)),
                "projects": sorted(list(projects)),
            }

        return result

