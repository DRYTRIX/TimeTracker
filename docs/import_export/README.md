# Import/Export System

## Quick Start

The TimeTracker Import/Export system enables seamless data migration, GDPR-compliant data exports, and comprehensive backup/restore functionality.

## Features

- 📥 **CSV Import** - Bulk import time entries
- 🔄 **Toggl/Harvest Import** - Direct integration with popular time trackers
- 📤 **GDPR Export** - Complete data export for compliance
- 🔍 **Filtered Export** - Export specific data with custom filters
- 💾 **Backup/Restore** - Full database backup (admin only)
- 📊 **History Tracking** - Monitor all import/export operations

## Quick Links

- **User Guide**: [IMPORT_EXPORT_GUIDE.md](../IMPORT_EXPORT_GUIDE.md)
- **Implementation Summary**: [IMPORT_EXPORT_IMPLEMENTATION_SUMMARY.md](../../IMPORT_EXPORT_IMPLEMENTATION_SUMMARY.md)
- **API Documentation**: See User Guide → API Documentation section

## For Users

### Accessing Import/Export

1. Click on your user menu (top right)
2. Select "Import/Export"
3. Choose your desired operation

### Common Tasks

**Import CSV File:**
1. Download the CSV template
2. Fill in your data
3. Upload the file
4. Check Import History for results

**Export Your Data (GDPR):**
1. Click "Export as JSON" or "Export as ZIP"
2. Wait for processing (usually < 1 minute)
3. Download the file when ready

**Import from Toggl:**
1. Get your API token from Toggl
2. Click "Import from Toggl"
3. Enter credentials and date range
4. Start import

## For Developers

### Project Structure

```
app/
├── models/
│   └── import_export.py          # DataImport & DataExport models
├── utils/
│   ├── data_import.py             # Import functions
│   └── data_export.py             # Export functions
├── routes/
│   └── import_export.py           # API endpoints
└── templates/
    └── import_export/
        └── index.html              # UI

migrations/
└── versions/
    └── 040_add_import_export_tables.py

tests/
├── test_import_export.py          # Integration tests
└── models/
    └── test_import_export_models.py  # Model tests

docs/
├── IMPORT_EXPORT_GUIDE.md         # Complete guide
└── import_export/
    └── README.md                   # This file
```

### Adding New Import Source

```python
# 1. Add import function in app/utils/data_import.py
def import_from_new_source(user_id, credentials, start_date, end_date, import_record):
    """Import from new time tracker"""
    import_record.start_processing()
    
    try:
        # Fetch data from API
        data = fetch_from_api(credentials)
        
        # Process each record
        for record in data:
            # Create TimeEntry
            time_entry = TimeEntry(...)
            db.session.add(time_entry)
            import_record.update_progress(...)
        
        db.session.commit()
        import_record.complete()
    except Exception as e:
        import_record.fail(str(e))

# 2. Add route in app/routes/import_export.py
@import_export_bp.route('/api/import/new-source', methods=['POST'])
@login_required
def import_new_source():
    data = request.get_json()
    # ... validation ...
    
    import_record = DataImport(
        user_id=current_user.id,
        import_type='new_source',
        source_file='...'
    )
    db.session.add(import_record)
    db.session.commit()
    
    summary = import_from_new_source(...)
    return jsonify({'success': True, 'import_id': import_record.id})

# 3. Add UI in app/templates/import_export/index.html
# Add button and modal form for the new source
```

### API Usage Examples

**Import CSV via API:**
```python
import requests

files = {'file': open('time_entries.csv', 'rb')}
response = requests.post(
    'http://localhost:8080/api/import/csv',
    files=files,
    cookies={'session': 'your_session_cookie'}
)
print(response.json())
```

**Export GDPR Data:**
```python
import requests

response = requests.post(
    'http://localhost:8080/api/export/gdpr',
    json={'format': 'json'},
    cookies={'session': 'your_session_cookie'}
)
result = response.json()
download_url = result['download_url']
```

**Check Import Status:**
```python
import requests

response = requests.get(
    f'http://localhost:8080/api/import/status/{import_id}',
    cookies={'session': 'your_session_cookie'}
)
status = response.json()
print(f"Status: {status['status']}")
print(f"Progress: {status['successful_records']}/{status['total_records']}")
```

### Running Tests

```bash
# Run all import/export tests
pytest tests/test_import_export.py -v

# Run model tests
pytest tests/models/test_import_export_models.py -v

# Run with coverage
pytest tests/test_import_export.py --cov=app.utils.data_import --cov=app.utils.data_export
```

### Database Migration

```bash
# Apply migration
flask db upgrade

# Or with Alembic
alembic upgrade head

# Rollback if needed
flask db downgrade
# or
alembic downgrade -1
```

## CSV Format Reference

### Required Columns
- `project_name` - Name of the project
- `start_time` - Start time (YYYY-MM-DD HH:MM:SS)

### Optional Columns
- `client_name` - Client name (defaults to project name)
- `task_name` - Task name
- `end_time` - End time
- `duration_hours` - Duration in hours
- `notes` - Description/notes
- `tags` - Semicolon-separated tags
- `billable` - true/false

### Example CSV

```csv
project_name,client_name,task_name,start_time,end_time,duration_hours,notes,tags,billable
Website Redesign,Acme Corp,Design,2024-01-15 09:00:00,2024-01-15 12:00:00,3.0,Homepage mockups,design;ui,true
Website Redesign,Acme Corp,Development,2024-01-15 14:00:00,2024-01-15 17:30:00,3.5,Implemented header,dev;frontend,true
```

## Security Notes

### Authentication
- All endpoints require authentication
- Users can only access their own data
- Admins can create backups and view all history

### Data Privacy
- Exports are private to the creating user
- Files expire after 7 days
- Secure storage in `/data/uploads`

### CSRF Protection
- All POST endpoints require CSRF token
- Automatically handled by the UI
- API clients must include CSRF token

## Troubleshooting

### Common Issues

**Import fails with "Invalid date format"**
- Use YYYY-MM-DD HH:MM:SS format
- Or ISO format: YYYY-MM-DDTHH:MM:SS

**Toggl import returns 401**
- Check API token is correct
- Verify workspace ID is valid
- Ensure you have access to the workspace

**Export download says "expired"**
- Exports expire after 7 days
- Create a new export

**Large import is slow**
- Imports are processed in batches
- Wait for completion (check Import History)
- Consider splitting into smaller date ranges

## Performance Tips

1. **Large Imports**
   - Split into smaller date ranges
   - Import during off-peak hours
   - Monitor Import History for progress

2. **Large Exports**
   - Use filtered exports for specific data
   - JSON is faster than ZIP for large datasets
   - Exports are generated asynchronously

3. **Storage Management**
   - Exports auto-delete after 7 days
   - Download important exports immediately
   - Backups should be stored externally

## Support

- **Documentation**: [IMPORT_EXPORT_GUIDE.md](../IMPORT_EXPORT_GUIDE.md)
- **Issues**: Report on GitHub
- **Questions**: Check FAQ in the main guide

## Version History

### Version 1.0 (October 31, 2024)
- Initial release
- CSV import
- Toggl integration
- Harvest integration
- GDPR export
- Filtered export
- Backup/restore
- Migration wizard
- History tracking

## License

Same as TimeTracker application.

