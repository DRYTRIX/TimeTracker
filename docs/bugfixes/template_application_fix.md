# Bug Fix: Template Application Error

## Issue
When users tried to select and apply a template from the start timer interface, they received an error message stating "can't apply the template".

## Root Cause
There were duplicate route definitions for the template API endpoints:

1. **In `app/routes/api.py` (lines 1440-1465)** - Registered first in the application
   - `/api/templates/<int:template_id>` (GET)
   - `/api/templates/<int:template_id>/use` (POST)
   - **Problem**: Missing `TimeEntryTemplate` import, causing `NameError` when routes were accessed

2. **In `app/routes/time_entry_templates.py` (lines 301-326)** - Registered later
   - Same routes with proper implementation
   - Had correct imports and error handling
   - Never executed due to duplicate route conflict

Since the `api_bp` blueprint was registered before `time_entry_templates_bp` in `app/__init__.py`, Flask used the broken routes from `api.py`, causing the error.

## Solution
Removed the duplicate route definitions from `app/routes/api.py` (lines 1440-1465), allowing the proper implementation in `app/routes/time_entry_templates.py` to be used.

### Code Changes
**File**: `app/routes/api.py`
- **Removed**: Lines 1440-1465 containing duplicate `/api/templates/<int:template_id>` routes
- **Reason**: Eliminate route conflict and use proper implementation

## Testing
All existing tests pass:
- ✅ `test_get_templates_api` - Get all templates
- ✅ `test_get_single_template_api` - Get specific template
- ✅ `test_use_template_api` - Mark template as used
- ✅ `test_start_timer_from_template` - Start timer from template

## Impact
- **Users can now successfully apply templates when starting timers**
- Template usage tracking works correctly
- No other functionality affected

## Date Fixed
October 31, 2025

