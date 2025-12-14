# Advanced Report Builder Implementation Summary

## Overview

This document summarizes the implementation of the Advanced Report Builder enhancements, including iterative report generation, custom field filtering, and improved scheduled report distribution.

## Features Implemented

### 1. Iterative Report Generation

**What it does:**
- Generates one report per unique value of a specified custom field (e.g., one report per salesman)
- Automatically extracts all unique values from clients and generates separate reports
- Perfect for scenarios where you need separate reports for each salesman, region, or other custom field value

**How to use:**
1. In Report Builder, create or edit a report
2. In the Save modal, enable "Iterative Report Generation"
3. Select the custom field to iterate over (e.g., "salesman")
4. When viewing the report, you'll see separate sections for each unique value

**Technical Details:**
- New fields in `SavedReportView` model:
  - `iterative_report_generation` (Boolean)
  - `iterative_custom_field_name` (String)
- Route: `/reports/builder/<view_id>` automatically detects iterative mode
- Template: `reports/iterative_view.html` displays all reports grouped by field value

### 2. Custom Field-Based Filtering

**What it does:**
- Filter reports by any custom field on clients
- Works in both Report Builder and Scheduled Reports
- Supports filtering for unpaid hours reports

**How to use:**
1. In Report Builder filters, select a custom field (e.g., "salesman")
2. Enter the value to filter by (e.g., "MM")
3. The report will only show data for clients matching that custom field value

**Technical Details:**
- Enhanced `generate_report_data()` function in `custom_reports.py`
- Supports filtering in `UnpaidHoursService`
- Works with both direct client custom fields and project->client relationships

### 3. Enhanced Scheduled Report Distribution

**What it does:**
- Supports three email distribution modes:
  - **Mapping**: Uses `SalesmanEmailMapping` table to map custom field values to email addresses
  - **Template**: Uses dynamic email templates (e.g., `{value}@test.de`)
  - **Single**: Sends all reports to the same recipients (fallback)

**How to use:**
1. Create a scheduled report with "Split by Custom Field" enabled
2. Choose email distribution mode:
   - **Mapping**: Set up mappings in Salesman Email Mapping (if available)
   - **Template**: Enter template like `{value}@test.de`
   - **Single**: Use default recipients field

**Technical Details:**
- New fields in `ReportEmailSchedule` model:
  - `email_distribution_mode` (String: 'mapping', 'template', 'single')
  - `recipient_email_template` (String: e.g., '{value}@test.de')
- Enhanced `_get_recipients_for_field_value()` method in `ScheduledReportService`
- Automatically resolves email addresses based on distribution mode

### 4. Improved Unpaid Hours Workflow

**What it does:**
- Clear checkbox option for "Unpaid Hours Only" in Report Builder
- Better integration with custom field filtering
- Clearer UI with helpful tooltips

**How to use:**
1. In Report Builder, select "Time Entries" as data source
2. Check "Unpaid Hours Only" checkbox
3. Optionally add custom field filter to segment by salesman
4. Preview or save the report

**Technical Details:**
- Uses `UnpaidHoursService` for accurate unpaid hours calculation
- Filters out entries that are:
  - Already in invoices (via `InvoiceItem.time_entry_ids`)
  - Marked as paid
  - Not billable

### 5. Enhanced Management Views

**What it does:**
- Comprehensive list of saved report views with edit/delete options
- Shows iterative generation status
- Better error handling in scheduled reports view
- Ability to fix or remove invalid scheduled reports

**How to use:**
1. Navigate to "Saved Views" from Report Builder
2. View all your saved reports with their features
3. Edit, view, or delete reports as needed
4. In Scheduled Reports, use the "Fix" button to resolve invalid schedules

**Technical Details:**
- Enhanced `list_saved_views()` route
- New `fix_scheduled()` route to handle invalid schedules
- Improved error handling in `list_scheduled()` route
- Validates saved views and filters out invalid ones

### 6. Better Error Handling

**What it does:**
- Prevents errors from breaking the Scheduled Reports view
- Validates report configurations before displaying
- Provides clear error messages and fix options

**Technical Details:**
- Enhanced error handling in `scheduled_reports.py`
- Validates JSON configs before processing
- Gracefully handles missing saved views
- Provides fix/remove options for invalid schedules

## Database Changes

### Migration: `090_enhance_report_builder_iteration`

**New Columns:**

1. **saved_report_views table:**
   - `iterative_report_generation` (Boolean, default: false)
   - `iterative_custom_field_name` (String, nullable)

2. **report_email_schedules table:**
   - `email_distribution_mode` (String, nullable) - Values: 'mapping', 'template', 'single'
   - `recipient_email_template` (String, nullable) - Template like '{value}@test.de'

## API Endpoints

### New/Enhanced Routes

1. **GET `/reports/builder/<view_id>`**
   - Now supports iterative report generation
   - Automatically detects if iterative mode is enabled

2. **GET `/api/reports/builder/custom-field-values`**
   - Returns unique values for a custom field
   - Query parameter: `field_name`

3. **POST `/reports/scheduled/<schedule_id>/fix`**
   - Fixes or removes invalid scheduled reports
   - Validates saved view and config

4. **POST `/reports/builder/save`**
   - Enhanced to accept iterative report generation settings
   - New fields: `iterative_report_generation`, `iterative_custom_field_name`

## Files Modified

### Backend
- `app/models/reporting.py` - Added new model fields
- `app/routes/custom_reports.py` - Enhanced with iterative generation
- `app/routes/scheduled_reports.py` - Improved error handling, added fix route
- `app/services/scheduled_report_service.py` - Enhanced email distribution
- `migrations/versions/090_enhance_report_builder_iteration.py` - New migration

### Frontend
- `app/templates/reports/builder.html` - Added iterative generation UI
- `app/templates/reports/saved_views_list.html` - Shows iterative status
- `app/templates/reports/scheduled.html` - Enhanced with distribution info and fix button
- `app/templates/reports/iterative_view.html` - New template for iterative reports

## Usage Examples

### Example 1: Unpaid Hours Report by Salesman

1. Create a new report in Report Builder
2. Select "Time Entries" as data source
3. Enable "Unpaid Hours Only"
4. Enable "Iterative Report Generation"
5. Select "salesman" as the custom field
6. Save the report
7. View the report to see separate sections for each salesman

### Example 2: Scheduled Reports with Email Mapping

1. Create a scheduled report
2. Enable "Split by Custom Field" and select "salesman"
3. Set email distribution mode to "mapping"
4. Ensure `SalesmanEmailMapping` entries exist (MM -> mm@test.de, PB -> pb@test.de)
5. Schedule will automatically send reports to the correct email for each salesman

### Example 3: Scheduled Reports with Email Template

1. Create a scheduled report
2. Enable "Split by Custom Field" and select "salesman"
3. Set email distribution mode to "template"
4. Enter template: `{value}@test.de`
5. Reports will be sent to MM@test.de, PB@test.de, etc.

## Testing Recommendations

1. **Unit Tests:**
   - Test iterative report generation logic
   - Test email distribution modes
   - Test custom field filtering

2. **Integration Tests:**
   - Test full workflow: create report → enable iterative → view report
   - Test scheduled reports with different distribution modes
   - Test error handling for invalid schedules

3. **Smoke Tests:**
   - Create unpaid hours report with custom field filter
   - Create iterative report and verify all values are shown
   - Create scheduled report and verify email distribution

## Known Limitations

1. **Email Mapping:**
   - Requires `SalesmanEmailMapping` entries to be set up manually
   - Falls back to default recipients if mapping not found

2. **Custom Field Values:**
   - Only extracts values from active clients
   - Values must be present in client custom_fields JSON

3. **Iterative Reports:**
   - Currently only works for time entries data source
   - Other data sources will need similar implementation

## Future Enhancements

1. Support iterative generation for other data sources (projects, invoices, etc.)
2. Add UI for managing email mappings directly in scheduled reports
3. Add preview for iterative reports before saving
4. Support multiple custom fields for iteration
5. Add export functionality for iterative reports

## Migration Instructions

1. Run the migration:
   ```bash
   flask db upgrade
   ```

2. Verify the migration:
   ```bash
   flask db current
   ```

3. Test the new features:
   - Create a test report with iterative generation
   - Create a test scheduled report with email distribution
   - Verify error handling works correctly

## Support

For issues or questions:
1. Check the error logs in `logs/timetracker.log`
2. Verify custom field values exist in client records
3. Check that email mappings are set up correctly (if using mapping mode)
4. Ensure saved report views have valid JSON configurations

