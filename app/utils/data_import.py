"""
Data import utilities for importing time tracking data from various sources
"""

import json
import csv
import logging
import requests
from datetime import datetime, timedelta
from io import StringIO
from flask import current_app
from app import db
from app.models import User, Project, TimeEntry, Task, Client, Expense, ExpenseCategory, Contact
from app.utils.db import safe_commit

logger = logging.getLogger(__name__)


class ImportError(Exception):
    """Custom exception for import errors"""

    pass


def import_csv_time_entries(user_id, csv_content, import_record):
    """
    Import time entries from CSV file

    Expected CSV format:
    project_name, task_name, start_time, end_time, duration_hours, notes, tags, billable

    Args:
        user_id: ID of the user importing data
        csv_content: String content of CSV file
        import_record: DataImport model instance to track progress

    Returns:
        Dictionary with import statistics
    """
    user = User.query.get(user_id)
    if not user:
        raise ImportError(f"User {user_id} not found")

    import_record.start_processing()

    # Parse CSV
    try:
        csv_reader = csv.DictReader(StringIO(csv_content))
        rows = list(csv_reader)
    except Exception as e:
        import_record.fail(f"Failed to parse CSV: {str(e)}")
        raise ImportError(f"Failed to parse CSV: {str(e)}")

    total = len(rows)
    successful = 0
    failed = 0
    errors = []

    import_record.update_progress(total, 0, 0)

    for idx, row in enumerate(rows):
        try:
            # Get or create project
            project_name = row.get("project_name", "").strip()
            if not project_name:
                raise ValueError("Project name is required")

            # Get or create client
            client_name = row.get("client_name", project_name).strip()
            client = Client.query.filter_by(name=client_name).first()
            if not client:
                client = Client(name=client_name)
                db.session.add(client)
                db.session.flush()

            # Get or create project
            project = Project.query.filter_by(name=project_name, client_id=client.id).first()
            if not project:
                project = Project(
                    name=project_name, client_id=client.id, billable=row.get("billable", "true").lower() == "true"
                )
                db.session.add(project)
                db.session.flush()

            # Get or create task (if provided)
            task = None
            task_name = row.get("task_name", "").strip()
            if task_name:
                task = Task.query.filter_by(name=task_name, project_id=project.id).first()
                if not task:
                    task = Task(name=task_name, project_id=project.id, status="in_progress")
                    db.session.add(task)
                    db.session.flush()

            # Parse times
            start_time = _parse_datetime(row.get("start_time", row.get("start", "")))
            end_time = _parse_datetime(row.get("end_time", row.get("end", "")))

            if not start_time:
                raise ValueError("Start time is required")

            # Create time entry
            time_entry = TimeEntry(
                user_id=user_id,
                project_id=project.id,
                task_id=task.id if task else None,
                start_time=start_time,
                end_time=end_time,
                notes=row.get("notes", row.get("description", "")).strip(),
                tags=row.get("tags", "").strip(),
                billable=row.get("billable", "true").lower() == "true",
                source="import",
            )

            # Handle duration
            if end_time:
                time_entry.calculate_duration()
            elif "duration_hours" in row:
                duration_hours = float(row["duration_hours"])
                time_entry.duration_seconds = int(duration_hours * 3600)
                if not end_time and start_time:
                    time_entry.end_time = start_time + timedelta(seconds=time_entry.duration_seconds)

            db.session.add(time_entry)
            successful += 1

            # Commit every 100 records
            if (idx + 1) % 100 == 0:
                db.session.commit()
                import_record.update_progress(total, successful, failed)

        except Exception as e:
            failed += 1
            error_msg = f"Row {idx + 1}: {str(e)}"
            errors.append(error_msg)
            import_record.add_error(error_msg, row)
            db.session.rollback()

    # Final commit
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        import_record.fail(f"Failed to commit final changes: {str(e)}")
        raise ImportError(f"Failed to commit changes: {str(e)}")

    # Update import record
    import_record.update_progress(total, successful, failed)

    if failed == 0:
        import_record.complete()
    elif successful > 0:
        import_record.partial_complete()
    else:
        import_record.fail("All records failed to import")

    summary = {"total": total, "successful": successful, "failed": failed, "errors": errors[:10]}  # First 10 errors
    import_record.set_summary(summary)

    return summary


def import_from_toggl(user_id, api_token, workspace_id, start_date, end_date, import_record):
    """
    Import time entries from Toggl Track

    Args:
        user_id: ID of the user importing data
        api_token: Toggl API token
        workspace_id: Toggl workspace ID
        start_date: Start date for import (datetime)
        end_date: End date for import (datetime)
        import_record: DataImport model instance to track progress

    Returns:
        Dictionary with import statistics
    """
    user = User.query.get(user_id)
    if not user:
        raise ImportError(f"User {user_id} not found")

    import_record.start_processing()

    # Fetch time entries from Toggl API
    try:
        # Toggl API v9 endpoint
        url = f"https://api.track.toggl.com/api/v9/me/time_entries"
        headers = {"Authorization": f"Basic {api_token}", "Content-Type": "application/json"}
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        time_entries = response.json()
    except requests.RequestException as e:
        import_record.fail(f"Failed to fetch data from Toggl: {str(e)}")
        raise ImportError(f"Failed to fetch data from Toggl: {str(e)}")

    total = len(time_entries)
    successful = 0
    failed = 0
    errors = []

    import_record.update_progress(total, 0, 0)

    # Fetch projects from Toggl to map IDs
    try:
        projects_url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/projects"
        projects_response = requests.get(projects_url, headers=headers, timeout=30)
        projects_response.raise_for_status()
        toggl_projects = {p["id"]: p for p in projects_response.json()}
    except (requests.RequestException, KeyError, ValueError) as e:
        logger.warning(f"Failed to fetch Toggl projects: {e}")
        toggl_projects = {}

    for idx, entry in enumerate(time_entries):
        try:
            # Map Toggl project to local project
            toggl_project_id = entry.get("project_id") or entry.get("pid")
            toggl_project = toggl_projects.get(toggl_project_id, {})
            project_name = toggl_project.get("name", "Imported Project")

            # Get or create client
            client_name = toggl_project.get("client_name", project_name)
            client = Client.query.filter_by(name=client_name).first()
            if not client:
                client = Client(name=client_name)
                db.session.add(client)
                db.session.flush()

            # Get or create project
            project = Project.query.filter_by(name=project_name, client_id=client.id).first()
            if not project:
                project = Project(name=project_name, client_id=client.id, billable=toggl_project.get("billable", True))
                db.session.add(project)
                db.session.flush()

            # Parse times
            start_time = datetime.fromisoformat(entry["start"].replace("Z", "+00:00"))

            # Toggl may have duration in seconds (positive) or negative for running timers
            duration_seconds = entry.get("duration", 0)
            if duration_seconds < 0:
                # Running timer, skip it
                continue

            end_time = None
            if "stop" in entry and entry["stop"]:
                end_time = datetime.fromisoformat(entry["stop"].replace("Z", "+00:00"))
            elif duration_seconds > 0:
                end_time = start_time + timedelta(seconds=duration_seconds)

            # Create time entry
            time_entry = TimeEntry(
                user_id=user_id,
                project_id=project.id,
                start_time=start_time.replace(tzinfo=None),  # Store as naive
                end_time=end_time.replace(tzinfo=None) if end_time else None,
                notes=entry.get("description", ""),
                tags=",".join(entry.get("tags", [])),
                billable=entry.get("billable", True),
                source="toggl",
                duration_seconds=duration_seconds if duration_seconds > 0 else None,
            )

            if end_time and not time_entry.duration_seconds:
                time_entry.calculate_duration()

            db.session.add(time_entry)
            successful += 1

            # Commit every 50 records
            if (idx + 1) % 50 == 0:
                db.session.commit()
                import_record.update_progress(total, successful, failed)

        except Exception as e:
            failed += 1
            error_msg = f"Entry {idx + 1}: {str(e)}"
            errors.append(error_msg)
            import_record.add_error(error_msg, entry)
            db.session.rollback()

    # Final commit
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        import_record.fail(f"Failed to commit final changes: {str(e)}")
        raise ImportError(f"Failed to commit changes: {str(e)}")

    # Update import record
    import_record.update_progress(total, successful, failed)

    if failed == 0:
        import_record.complete()
    elif successful > 0:
        import_record.partial_complete()
    else:
        import_record.fail("All records failed to import")

    summary = {"total": total, "successful": successful, "failed": failed, "errors": errors[:10]}
    import_record.set_summary(summary)

    return summary


def import_from_harvest(user_id, account_id, api_token, start_date, end_date, import_record):
    """
    Import time entries from Harvest

    Args:
        user_id: ID of the user importing data
        account_id: Harvest account ID
        api_token: Harvest API token
        start_date: Start date for import (datetime)
        end_date: End date for import (datetime)
        import_record: DataImport model instance to track progress

    Returns:
        Dictionary with import statistics
    """
    user = User.query.get(user_id)
    if not user:
        raise ImportError(f"User {user_id} not found")

    import_record.start_processing()

    # Fetch time entries from Harvest API
    try:
        url = "https://api.harvestapp.com/v2/time_entries"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Harvest-Account-ID": str(account_id),
            "User-Agent": "TimeTracker Import",
        }
        params = {"from": start_date.strftime("%Y-%m-%d"), "to": end_date.strftime("%Y-%m-%d"), "per_page": 100}

        all_entries = []
        page = 1

        while True:
            params["page"] = page
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            all_entries.extend(data.get("time_entries", []))

            # Check if there are more pages
            if data.get("links", {}).get("next"):
                page += 1
            else:
                break

        time_entries = all_entries
    except requests.RequestException as e:
        import_record.fail(f"Failed to fetch data from Harvest: {str(e)}")
        raise ImportError(f"Failed to fetch data from Harvest: {str(e)}")

    total = len(time_entries)
    successful = 0
    failed = 0
    errors = []

    import_record.update_progress(total, 0, 0)

    # Fetch projects from Harvest to map IDs
    try:
        projects_url = "https://api.harvestapp.com/v2/projects"
        projects_response = requests.get(projects_url, headers=headers, timeout=30)
        projects_response.raise_for_status()
        harvest_projects = {p["id"]: p for p in projects_response.json().get("projects", [])}
    except (requests.RequestException, KeyError, ValueError) as e:
        logger.warning(f"Failed to fetch Harvest projects: {e}")
        harvest_projects = {}

    # Fetch clients from Harvest
    try:
        clients_url = "https://api.harvestapp.com/v2/clients"
        clients_response = requests.get(clients_url, headers=headers, timeout=30)
        clients_response.raise_for_status()
        harvest_clients = {c["id"]: c for c in clients_response.json().get("clients", [])}
    except (requests.RequestException, KeyError, ValueError) as e:
        logger.warning(f"Failed to fetch Harvest clients: {e}")
        harvest_clients = {}

    for idx, entry in enumerate(time_entries):
        try:
            # Map Harvest project to local project
            harvest_project_id = entry.get("project", {}).get("id")
            harvest_project = harvest_projects.get(harvest_project_id, {})
            project_name = harvest_project.get("name", "Imported Project")

            # Get client
            harvest_client_id = harvest_project.get("client", {}).get("id")
            harvest_client = harvest_clients.get(harvest_client_id, {})
            client_name = harvest_client.get("name", project_name)

            # Get or create client
            client = Client.query.filter_by(name=client_name).first()
            if not client:
                client = Client(name=client_name)
                db.session.add(client)
                db.session.flush()

            # Get or create project
            project = Project.query.filter_by(name=project_name, client_id=client.id).first()
            if not project:
                project = Project(
                    name=project_name, client_id=client.id, billable=harvest_project.get("is_billable", True)
                )
                db.session.add(project)
                db.session.flush()

            # Get or create task
            task = None
            task_name = entry.get("task", {}).get("name")
            if task_name:
                task = Task.query.filter_by(name=task_name, project_id=project.id).first()
                if not task:
                    task = Task(name=task_name, project_id=project.id, status="in_progress")
                    db.session.add(task)
                    db.session.flush()

            # Parse times
            # Harvest provides date and hours
            spent_date = datetime.strptime(entry["spent_date"], "%Y-%m-%d")
            hours = float(entry.get("hours", 0))

            # Create start/end times (use midday as default start time)
            start_time = spent_date.replace(hour=12, minute=0, second=0)
            duration_seconds = int(hours * 3600)
            end_time = start_time + timedelta(seconds=duration_seconds)

            # Create time entry
            time_entry = TimeEntry(
                user_id=user_id,
                project_id=project.id,
                task_id=task.id if task else None,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                notes=entry.get("notes", ""),
                billable=entry.get("billable", True),
                source="harvest",
            )

            db.session.add(time_entry)
            successful += 1

            # Commit every 50 records
            if (idx + 1) % 50 == 0:
                db.session.commit()
                import_record.update_progress(total, successful, failed)

        except Exception as e:
            failed += 1
            error_msg = f"Entry {idx + 1}: {str(e)}"
            errors.append(error_msg)
            import_record.add_error(error_msg, entry)
            db.session.rollback()

    # Final commit
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        import_record.fail(f"Failed to commit final changes: {str(e)}")
        raise ImportError(f"Failed to commit changes: {str(e)}")

    # Update import record
    import_record.update_progress(total, successful, failed)

    if failed == 0:
        import_record.complete()
    elif successful > 0:
        import_record.partial_complete()
    else:
        import_record.fail("All records failed to import")

    summary = {"total": total, "successful": successful, "failed": failed, "errors": errors[:10]}
    import_record.set_summary(summary)

    return summary


def restore_from_backup(user_id, backup_file_path):
    """
    Restore data from a backup file

    Args:
        user_id: ID of the admin user performing restore
        backup_file_path: Path to backup JSON file

    Returns:
        Dictionary with restore statistics
    """
    user = User.query.get(user_id)
    if not user or not user.is_admin:
        raise ImportError("Only admin users can restore from backup")

    # Load backup file
    try:
        with open(backup_file_path, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
    except Exception as e:
        raise ImportError(f"Failed to load backup file: {str(e)}")

    # Validate backup format
    if "backup_info" not in backup_data:
        raise ImportError("Invalid backup file format")

    statistics = {"users": 0, "clients": 0, "projects": 0, "time_entries": 0, "tasks": 0, "expenses": 0, "errors": []}

    # Note: This is a simplified restore. In production, you'd want more sophisticated
    # handling of conflicts, relationships, and potentially a transaction-based approach

    current_app.logger.info(f"Starting restore from backup by user {user.username}")

    return statistics


def _parse_datetime(datetime_str):
    """
    Parse datetime string in various formats

    Supports:
    - ISO 8601: 2024-01-01T12:00:00
    - Date only: 2024-01-01 (assumes midnight)
    - Various formats
    """
    if not datetime_str or not isinstance(datetime_str, str):
        return None

    datetime_str = datetime_str.strip()

    # Try common formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue

    # Try ISO format with timezone
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)  # Convert to naive datetime
    except (ValueError, AttributeError) as e:
        logger.debug(f"Could not parse datetime string '{datetime_str}' as ISO format: {e}")
        pass

    return None


def import_csv_clients(user_id, csv_content, import_record, skip_duplicates=True, duplicate_detection_fields=None):
    """
    Import clients from CSV file

    Expected CSV format:
    name,description,contact_person,email,phone,address,default_hourly_rate,status,prepaid_hours_monthly,prepaid_reset_day,custom_field_1,custom_field_2,...,contact_1_first_name,contact_1_last_name,contact_1_email,contact_1_phone,contact_1_title,contact_1_role,contact_1_is_primary,contact_2_first_name,...

    For multiple contacts, use columns like:
    - contact_1_first_name, contact_1_last_name, contact_1_email, etc.
    - contact_2_first_name, contact_2_last_name, contact_2_email, etc.
    - Up to contact_N_* for as many contacts as needed

    Custom fields can be specified as columns with names like:
    - custom_field_<field_name> (e.g., custom_field_erp_id, custom_field_debtor_number)

    Args:
        user_id: ID of the user importing data
        csv_content: String content of CSV file
        import_record: DataImport model instance to track progress
        skip_duplicates: If True, skip clients that already exist
        duplicate_detection_fields: List of field names to use for duplicate detection.
            Can include 'name' for client name, or custom field names (e.g., 'debtor_number').
            If None, defaults to ['name'] plus all custom fields found in the CSV.
            Examples: ['debtor_number'], ['name', 'debtor_number'], ['erp_id']

    Returns:
        Dictionary with import statistics
    """
    from decimal import Decimal, InvalidOperation
    
    user = User.query.get(user_id)
    if not user:
        raise ImportError(f"User {user_id} not found")

    import_record.start_processing()

    # Parse CSV
    try:
        csv_reader = csv.DictReader(StringIO(csv_content))
        rows = list(csv_reader)
    except Exception as e:
        import_record.fail(f"Failed to parse CSV: {str(e)}")
        raise ImportError(f"Failed to parse CSV: {str(e)}")

    total = len(rows)
    successful = 0
    failed = 0
    skipped = 0
    errors = []

    import_record.update_progress(total, 0, 0)

    for idx, row in enumerate(rows):
        try:
            # Get client name (required)
            client_name = row.get("name", "").strip()
            if not client_name:
                raise ValueError("Client name is required")

            # Check for duplicates if skip_duplicates is True
            if skip_duplicates:
                existing_client = None
                
                # Determine which fields to use for duplicate detection
                if duplicate_detection_fields is not None:
                    # Use explicitly specified fields
                    detection_fields = duplicate_detection_fields
                else:
                    # Default: check by name + all custom fields found in CSV
                    detection_fields = ['name']
                    # Add all custom fields found in CSV
                    for key in row.keys():
                        if key.startswith("custom_field_"):
                            field_name = key.replace("custom_field_", "")
                            if field_name not in detection_fields:
                                detection_fields.append(field_name)
                
                # Check each specified field for duplicates
                for field in detection_fields:
                    if field == 'name':
                        # Check by client name
                        existing_client = Client.query.filter_by(name=client_name).first()
                        if existing_client:
                            break
                    else:
                        # Check by custom field
                        csv_key = f"custom_field_{field}"
                        field_value = row.get(csv_key, "").strip()
                        if field_value:
                            # Check if any client has this custom field value
                            all_clients = Client.query.all()
                            for client in all_clients:
                                if client.custom_fields and client.custom_fields.get(field) == field_value:
                                    existing_client = client
                                    break
                            if existing_client:
                                break
                
                if existing_client:
                    skipped += 1
                    errors.append(f"Row {idx + 1}: Client '{client_name}' already exists (skipped)")
                    continue

            # Get or create client
            client = Client.query.filter_by(name=client_name).first()
            is_new = False
            
            if not client:
                client = Client(
                    name=client_name,
                    description=row.get("description", "").strip() or None,
                    contact_person=row.get("contact_person", "").strip() or None,
                    email=row.get("email", "").strip() or None,
                    phone=row.get("phone", "").strip() or None,
                    address=row.get("address", "").strip() or None,
                )
                is_new = True
            else:
                # Update existing client
                if row.get("description"):
                    client.description = row.get("description", "").strip() or None
                if row.get("contact_person"):
                    client.contact_person = row.get("contact_person", "").strip() or None
                if row.get("email"):
                    client.email = row.get("email", "").strip() or None
                if row.get("phone"):
                    client.phone = row.get("phone", "").strip() or None
                if row.get("address"):
                    client.address = row.get("address", "").strip() or None

            # Set default hourly rate
            if row.get("default_hourly_rate"):
                try:
                    client.default_hourly_rate = Decimal(str(row.get("default_hourly_rate")))
                except (InvalidOperation, ValueError):
                    pass

            # Set status
            status = row.get("status", "active").strip().lower()
            if status in ["active", "inactive", "archived"]:
                client.status = status

            # Set prepaid hours
            if row.get("prepaid_hours_monthly"):
                try:
                    client.prepaid_hours_monthly = Decimal(str(row.get("prepaid_hours_monthly")))
                except (InvalidOperation, ValueError):
                    pass

            # Set prepaid reset day
            if row.get("prepaid_reset_day"):
                try:
                    reset_day = int(row.get("prepaid_reset_day"))
                    client.prepaid_reset_day = max(1, min(28, reset_day))
                except (ValueError, TypeError):
                    pass

            # Handle custom fields
            custom_fields = {}
            for key, value in row.items():
                if key.startswith("custom_field_"):
                    field_name = key.replace("custom_field_", "")
                    field_value = value.strip() if value else None
                    if field_value:
                        custom_fields[field_name] = field_value
            
            if custom_fields:
                if client.custom_fields:
                    client.custom_fields.update(custom_fields)
                else:
                    client.custom_fields = custom_fields

            if is_new:
                db.session.add(client)
            db.session.flush()

            # Handle contacts
            # Find all contact columns (contact_N_field_name)
            contact_numbers = set()
            for key in row.keys():
                if key.startswith("contact_") and "_" in key:
                    parts = key.split("_")
                    if len(parts) >= 3 and parts[0] == "contact" and parts[1].isdigit():
                        contact_numbers.add(int(parts[1]))

            # Process each contact
            for contact_num in sorted(contact_numbers):
                first_name = row.get(f"contact_{contact_num}_first_name", "").strip()
                last_name = row.get(f"contact_{contact_num}_last_name", "").strip()
                
                if not first_name and not last_name:
                    continue  # Skip if no name provided

                # Use first_name as fallback if last_name is missing
                if not last_name:
                    last_name = first_name
                    first_name = ""
                elif not first_name:
                    first_name = last_name
                    last_name = ""

                # Check if contact already exists
                existing_contact = Contact.query.filter_by(
                    client_id=client.id,
                    first_name=first_name,
                    last_name=last_name
                ).first()

                if existing_contact:
                    # Update existing contact
                    contact = existing_contact
                else:
                    # Create new contact
                    contact = Contact(
                        client_id=client.id,
                        first_name=first_name,
                        last_name=last_name,
                        created_by=user_id
                    )
                    db.session.add(contact)

                # Update contact fields
                if row.get(f"contact_{contact_num}_email"):
                    contact.email = row.get(f"contact_{contact_num}_email", "").strip() or None
                if row.get(f"contact_{contact_num}_phone"):
                    contact.phone = row.get(f"contact_{contact_num}_phone", "").strip() or None
                if row.get(f"contact_{contact_num}_mobile"):
                    contact.mobile = row.get(f"contact_{contact_num}_mobile", "").strip() or None
                if row.get(f"contact_{contact_num}_title"):
                    contact.title = row.get(f"contact_{contact_num}_title", "").strip() or None
                if row.get(f"contact_{contact_num}_department"):
                    contact.department = row.get(f"contact_{contact_num}_department", "").strip() or None
                if row.get(f"contact_{contact_num}_role"):
                    contact.role = row.get(f"contact_{contact_num}_role", "").strip() or "contact"
                if row.get(f"contact_{contact_num}_is_primary"):
                    is_primary = str(row.get(f"contact_{contact_num}_is_primary", "")).lower() in ("true", "1", "yes")
                    if is_primary:
                        # Unset other primary contacts
                        Contact.query.filter_by(client_id=client.id, is_primary=True).update({"is_primary": False})
                        contact.is_primary = True
                if row.get(f"contact_{contact_num}_address"):
                    contact.address = row.get(f"contact_{contact_num}_address", "").strip() or None
                if row.get(f"contact_{contact_num}_notes"):
                    contact.notes = row.get(f"contact_{contact_num}_notes", "").strip() or None
                if row.get(f"contact_{contact_num}_tags"):
                    contact.tags = row.get(f"contact_{contact_num}_tags", "").strip() or None

            successful += 1

            # Commit every 50 records
            if (idx + 1) % 50 == 0:
                db.session.commit()
                import_record.update_progress(total, successful, failed)

        except Exception as e:
            failed += 1
            error_msg = f"Row {idx + 1}: {str(e)}"
            errors.append(error_msg)
            import_record.add_error(error_msg, row)
            db.session.rollback()

    # Final commit
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        import_record.fail(f"Failed to commit final changes: {str(e)}")
        raise ImportError(f"Failed to commit changes: {str(e)}")

    # Update import record
    import_record.update_progress(total, successful, failed)

    if failed == 0:
        import_record.complete()
    elif successful > 0:
        import_record.partial_complete()
    else:
        import_record.fail("All records failed to import")

    summary = {
        "total": total,
        "successful": successful,
        "failed": failed,
        "skipped": skipped,
        "errors": errors[:10]  # First 10 errors
    }
    import_record.set_summary(summary)

    return summary
