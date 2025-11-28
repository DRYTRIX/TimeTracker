"""
Data import utilities for importing time tracking data from various sources
"""

import json
import csv
import requests
from datetime import datetime, timedelta
from io import StringIO
from flask import current_app
from app import db
from app.models import User, Project, TimeEntry, Task, Client, Expense, ExpenseCategory
from app.utils.db import safe_commit


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
    except:
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
    except:
        harvest_projects = {}

    # Fetch clients from Harvest
    try:
        clients_url = "https://api.harvestapp.com/v2/clients"
        clients_response = requests.get(clients_url, headers=headers, timeout=30)
        clients_response.raise_for_status()
        harvest_clients = {c["id"]: c for c in clients_response.json().get("clients", [])}
    except:
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
    except:
        pass

    return None
