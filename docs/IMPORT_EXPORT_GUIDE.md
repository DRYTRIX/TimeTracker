# Import/Export System Guide

## Overview

The TimeTracker Import/Export system provides comprehensive functionality for migrating data between time tracking systems, exporting data for GDPR compliance, and creating backups for disaster recovery.

## Features

### Import Features

- **CSV Import**: Bulk import time entries from CSV files
- **Toggl Track Import**: Direct integration with Toggl Track API
- **Harvest Import**: Direct integration with Harvest API
- **Backup Restore**: Restore from previous backups (admin only)
- **Migration Wizard**: Step-by-step import process with preview

### Export Features

- **GDPR Data Export**: Complete export of all user data for compliance
- **Filtered Export**: Export specific data with custom filters
- **Full Backup**: Complete database backup (admin only)
- **Multiple Formats**: JSON, CSV, and ZIP formats supported

## User Guide

### Accessing Import/Export

Navigate to the Import/Export page:
1. Click on your user menu in the top right
2. Select "Import/Export" from the dropdown
3. Or navigate directly to `/import-export`

---

## Import Guide

### CSV Import

#### CSV Format

The CSV file should have the following columns:

```csv
project_name,client_name,task_name,start_time,end_time,duration_hours,notes,tags,billable
Project A,Client A,Task 1,2024-01-01 09:00:00,2024-01-01 10:30:00,1.5,Meeting notes,meeting;planning,true
Project B,Client B,,2024-01-01 14:00:00,2024-01-01 16:00:00,2.0,Development work,dev;coding,true
```

#### Column Descriptions

| Column | Required | Description |
|--------|----------|-------------|
| `project_name` | Yes | Name of the project |
| `client_name` | No | Client name (defaults to project name if not provided) |
| `task_name` | No | Optional task name |
| `start_time` | Yes | Start time (YYYY-MM-DD HH:MM:SS or ISO format) |
| `end_time` | No | End time (leave empty if providing duration_hours) |
| `duration_hours` | No | Duration in hours (alternative to end_time) |
| `notes` | No | Notes or description |
| `tags` | No | Comma-separated tags (use semicolon to separate multiple tags) |
| `billable` | No | true/false (defaults to true) |

#### Supported Date Formats

- `YYYY-MM-DD HH:MM:SS` (e.g., 2024-01-01 09:00:00)
- `YYYY-MM-DDTHH:MM:SS` (ISO format)
- `YYYY-MM-DD` (assumes midnight)
- `DD/MM/YYYY HH:MM:SS`
- `MM/DD/YYYY HH:MM:SS`

#### Steps to Import CSV

1. Download the CSV template: Click "Download Template"
2. Fill in your time entries data
3. Click "Choose CSV File" and select your file
4. The import will start automatically
5. Check the Import History section for results

#### Handling Errors

If some records fail to import:
- Check the Import History for error details
- Common errors include:
  - Invalid date formats
  - Missing required fields (project_name, start_time)
  - Invalid duration values
- Fix the errors in your CSV and re-import

---

### Toggl Track Import

#### Prerequisites

You'll need:
- Toggl Track API token (find in Profile Settings → API Token)
- Workspace ID (find in workspace settings)

#### Steps to Import from Toggl

1. Click "Import from Toggl"
2. Enter your API token
3. Enter your Workspace ID
4. Select date range for import
5. Click "Import"
6. Wait for the import to complete

#### What Gets Imported

- All time entries within the selected date range
- Projects (automatically created if they don't exist)
- Clients (linked to projects)
- Tasks (if present in Toggl)
- Tags
- Notes/descriptions
- Billable status

#### API Rate Limits

Toggl has rate limits on their API. For large imports:
- Import is done in batches of 50 entries
- Imports may take several minutes for large datasets
- If import fails due to rate limits, wait a few minutes and try again

---

### Harvest Import

#### Prerequisites

You'll need:
- Harvest Account ID (find in Account Settings)
- Personal Access Token (create in Developers → Personal Access Tokens)

#### Steps to Import from Harvest

1. Click "Import from Harvest"
2. Enter your Account ID
3. Enter your API Token
4. Select date range for import
5. Click "Import"
6. Wait for the import to complete

#### What Gets Imported

- All time entries within the selected date range
- Projects (automatically created if they don't exist)
- Clients (linked to projects)
- Tasks (if present in Harvest)
- Notes
- Billable status
- Hours tracked

#### Notes

- Harvest provides daily totals rather than start/end times
- Imported entries will have a default start time of 12:00 PM on the tracked date
- Duration is preserved accurately

---

## Export Guide

### GDPR Data Export

Export all your personal data for compliance with data protection regulations.

#### What's Included

- User profile information
- All time entries
- Projects you've worked on
- Tasks assigned to you
- Expenses and mileage records
- Comments and notes
- Focus sessions
- Saved filters and preferences
- Calendar events
- Weekly goals

#### Steps to Export

1. Choose export format:
   - **JSON**: Single file with all data in JSON format
   - **ZIP**: Multiple CSV files + JSON file in a ZIP archive
2. Click the export button
3. Wait for export to complete (usually < 1 minute)
4. Click "Download" when ready
5. Exports expire after 7 days

#### Export Formats

**JSON Export:**
```json
{
  "export_info": {
    "user_id": 1,
    "username": "john.doe",
    "export_date": "2024-01-15T10:30:00",
    "export_type": "GDPR Full Data Export"
  },
  "user_profile": {...},
  "time_entries": [...],
  "projects": [...]
}
```

**ZIP Export:**
- `export.json` - Complete data in JSON
- `time_entries.csv` - Time entries
- `projects.csv` - Projects
- `expenses.csv` - Expenses
- etc.

---

### Filtered Export

Export specific data with custom filters.

#### Available Filters

- **Date Range**: Export data within specific dates
- **Project**: Export only specific project data
- **Billable Only**: Export only billable entries
- **Data Types**: Choose what to export (time entries, expenses, etc.)

#### Steps to Export

1. Click "Export with Filters"
2. Configure your filters
3. Choose export format (JSON or CSV)
4. Click "Export"
5. Download when ready

---

### Backup & Restore (Admin Only)

#### Creating Backups

Admins can create full database backups:

1. Click "Create Backup"
2. Wait for backup to complete
3. Download the backup file
4. Store securely (backup includes all system data)

#### What's Included in Backups

- All users
- All projects and clients
- All time entries
- All expenses and related data
- Tasks and comments
- System settings
- Invoices and payments

#### Restoring from Backup

⚠️ **Warning**: Restore will overwrite existing data!

1. Click "Restore Backup"
2. Select backup file (JSON format)
3. Confirm restoration
4. Wait for restore to complete
5. Review Import History for results

#### Best Practices

- Create backups regularly (daily or weekly)
- Test restore process in non-production environment
- Store backups in multiple locations
- Keep backups for at least 30 days

---

## API Documentation

### Authentication

All API endpoints require authentication. Include session cookies or API token in requests.

### Import Endpoints

#### CSV Import

```http
POST /api/import/csv
Content-Type: multipart/form-data

file: <csv_file>
```

**Response:**
```json
{
  "success": true,
  "import_id": 123,
  "summary": {
    "total": 100,
    "successful": 95,
    "failed": 5,
    "errors": []
  }
}
```

#### Toggl Import

```http
POST /api/import/toggl
Content-Type: application/json

{
  "api_token": "your_api_token",
  "workspace_id": "12345",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

#### Harvest Import

```http
POST /api/import/harvest
Content-Type: application/json

{
  "account_id": "12345",
  "api_token": "your_api_token",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

#### Import Status

```http
GET /api/import/status/<import_id>
```

**Response:**
```json
{
  "id": 123,
  "user": "john.doe",
  "import_type": "csv",
  "status": "completed",
  "total_records": 100,
  "successful_records": 95,
  "failed_records": 5,
  "started_at": "2024-01-15T10:00:00",
  "completed_at": "2024-01-15T10:05:00"
}
```

#### Import History

```http
GET /api/import/history
```

### Export Endpoints

#### GDPR Export

```http
POST /api/export/gdpr
Content-Type: application/json

{
  "format": "json"  // or "zip"
}
```

**Response:**
```json
{
  "success": true,
  "export_id": 456,
  "filename": "gdpr_export_john.doe_20240115_103000.json",
  "download_url": "/api/export/download/456"
}
```

#### Filtered Export

```http
POST /api/export/filtered
Content-Type: application/json

{
  "format": "json",  // or "csv"
  "filters": {
    "include_time_entries": true,
    "include_projects": false,
    "include_expenses": true,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "project_id": null,
    "billable_only": false
  }
}
```

#### Create Backup (Admin Only)

```http
POST /api/export/backup
```

#### Download Export

```http
GET /api/export/download/<export_id>
```

Returns the export file for download.

#### Export Status

```http
GET /api/export/status/<export_id>
```

#### Export History

```http
GET /api/export/history
```

---

## Troubleshooting

### Import Issues

**Problem**: CSV import fails with "Invalid date format"
- **Solution**: Check date format matches supported formats. Use YYYY-MM-DD HH:MM:SS

**Problem**: "Project name is required" error
- **Solution**: Ensure every row has a project_name value

**Problem**: Toggl/Harvest import fails
- **Solution**: 
  - Verify API credentials are correct
  - Check date range is valid
  - Ensure you have access to the workspace/account

**Problem**: Import stuck in "processing" status
- **Solution**: 
  - Wait a few minutes (large imports take time)
  - Check Import History for errors
  - Try re-importing with smaller date range

### Export Issues

**Problem**: Export download says "expired"
- **Solution**: Create a new export (exports expire after 7 days)

**Problem**: Export file is empty
- **Solution**: Check that you have data in the selected date range/filters

**Problem**: ZIP export won't extract
- **Solution**: Ensure download completed fully, try re-downloading

---

## Database Schema

### DataImport Model

```python
class DataImport:
    id: int
    user_id: int
    import_type: str  # 'csv', 'toggl', 'harvest', 'backup'
    source_file: str
    status: str  # 'pending', 'processing', 'completed', 'failed', 'partial'
    total_records: int
    successful_records: int
    failed_records: int
    error_log: str  # JSON
    import_summary: str  # JSON
    started_at: datetime
    completed_at: datetime
```

### DataExport Model

```python
class DataExport:
    id: int
    user_id: int
    export_type: str  # 'full', 'filtered', 'backup', 'gdpr'
    export_format: str  # 'json', 'csv', 'xlsx', 'zip'
    file_path: str
    file_size: int
    status: str  # 'pending', 'processing', 'completed', 'failed'
    filters: str  # JSON
    record_count: int
    error_message: str
    created_at: datetime
    completed_at: datetime
    expires_at: datetime
```

---

## Security & Privacy

### Data Protection

- All exports are private to the user who created them
- Exports expire after 7 days
- Export files are stored securely in `/data/uploads/exports`
- Only authenticated users can access their own exports

### Admin Privileges

- Backups require admin privileges
- Admins can see all import/export history
- Backup files contain ALL system data

### GDPR Compliance

The GDPR export feature provides:
- Complete data portability
- Machine-readable format (JSON)
- Human-readable format (CSV in ZIP)
- All personal data associated with the user
- Compliance with Article 20 (Right to Data Portability)

---

## Migration Wizard

The Migration Wizard provides a guided experience for importing data from other time trackers.

### Step 1: Choose Source

Select your source time tracker:
- Toggl Track
- Harvest
- CSV file

### Step 2: Enter Credentials

Provide API credentials for the source system.

### Step 3: Preview Data

See a preview of what will be imported:
- Number of entries
- Date range
- Projects and clients

### Step 4: Confirm Import

Review and start the import process.

### Step 5: Monitor Progress

Watch real-time import progress and see results.

---

## Developer Guide

### Adding New Import Sources

To add support for a new time tracker:

1. Create import function in `app/utils/data_import.py`:

```python
def import_from_new_tracker(user_id, credentials, start_date, end_date, import_record):
    """Import from new time tracker"""
    # Fetch data from API
    # Transform to TimeTracker format
    # Create records in database
    # Update import_record progress
    pass
```

2. Add route in `app/routes/import_export.py`:

```python
@import_export_bp.route('/api/import/new-tracker', methods=['POST'])
@login_required
def import_new_tracker():
    # Handle import request
    pass
```

3. Add UI in template `app/templates/import_export/index.html`

### Adding New Export Formats

To support a new export format:

1. Add export function in `app/utils/data_export.py`
2. Update export routes to handle new format
3. Add format option in UI

---

## FAQ

**Q: How long are exports stored?**
A: Exports are automatically deleted after 7 days.

**Q: Can I schedule automatic exports?**
A: Not currently, but this feature is planned.

**Q: What happens to duplicates during import?**
A: Duplicate entries are imported as separate records. Use the date range and filters carefully.

**Q: Can I import from multiple Toggl workspaces?**
A: Yes, import from each workspace separately.

**Q: Are imported entries marked differently?**
A: Yes, imported entries have a `source` field set to 'toggl', 'harvest', 'import', etc.

**Q: Can I undo an import?**
A: No automatic undo, but you can filter by source and manually delete imported entries if needed.

---

## Support

For additional help:
- Check the main [README](../README.md)
- Review [API documentation](../docs/API.md)
- Report issues on GitHub
- Contact your system administrator

---

## Changelog

### Version 1.0 (Initial Release)
- CSV import functionality
- Toggl Track integration
- Harvest integration
- GDPR data export
- Filtered exports
- Backup/restore functionality
- Migration wizard
- Import/export history tracking

