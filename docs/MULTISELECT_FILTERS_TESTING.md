# Multi-Select Filters Testing Guide

## Overview
This document provides testing instructions for the multi-select filter functionality implemented for Kanban and Tasks views.

## Feature Description
Users can now select multiple projects and/or multiple users to filter tasks in both Kanban and Tasks views, instead of being limited to viewing one project/user at a time or all items.

## Test Scenarios

### 1. Basic Multi-Select Functionality

#### Kanban View (`/kanban`)
- [ ] **Test 1.1**: Open Kanban view and click on the "Project" dropdown
  - Expected: Dropdown opens showing checkboxes for all active projects
  - Expected: Search box appears (if more than 5 projects exist)
  - Expected: "All" checkbox at the top
  - Expected: "Clear" and "Apply" buttons at the bottom

- [ ] **Test 1.2**: Select multiple projects (e.g., 2-3 projects)
  - Expected: Checkboxes become checked
  - Expected: Button label updates to show "Selected: X"
  - Expected: Click "Apply" button
  - Expected: Dropdown closes
  - Expected: Page reloads with filtered tasks
  - Expected: URL contains `?project_ids=1,2,3`
  - Expected: Only tasks from selected projects are displayed

- [ ] **Test 1.3**: Select multiple users in "Assigned To" dropdown
  - Expected: Similar behavior to project selection
  - Expected: URL contains `?user_ids=4,5,6`
  - Expected: Only tasks assigned to selected users are displayed

- [ ] **Test 1.4**: Combine project and user filters
  - Expected: URL contains both `?project_ids=1,2&user_ids=4,5`
  - Expected: Tasks match BOTH criteria (AND logic)

#### Tasks View (`/tasks`)
- [ ] **Test 1.5**: Repeat tests 1.1-1.4 in Tasks view
  - Expected: AJAX filtering (no page reload)
  - Expected: Task list updates without full page refresh
  - Expected: URL updates in browser address bar
  - Expected: Loading state shows during filtering

### 2. Search Functionality in Multi-Select

- [ ] **Test 2.1**: Open project dropdown with 10+ projects
  - Expected: Search box is visible
  - Type "test" in search box
  - Expected: Only projects with "test" in name are shown
  - Expected: Other projects are hidden
  - Expected: Search is case-insensitive

- [ ] **Test 2.2**: Clear search
  - Expected: All projects become visible again

### 3. "All" Checkbox Functionality

- [ ] **Test 3.1**: Click "All" checkbox when none are selected
  - Expected: All items become checked
  - Expected: Label shows "All"

- [ ] **Test 3.2**: Click "All" checkbox when all are selected
  - Expected: All items become unchecked
  - Expected: Label shows "All Projects" or "All Users"

- [ ] **Test 3.3**: Manually select all items individually
  - Expected: "All" checkbox becomes checked automatically

### 4. Clear Button

- [ ] **Test 4.1**: Select several items, then click "Clear"
  - Expected: All checkboxes become unchecked
  - Expected: Label resets to placeholder text
  - Expected: "All" checkbox becomes unchecked

### 5. Backward Compatibility

- [ ] **Test 5.1**: Open old URL format `?project_id=5`
  - Expected: Single project filter works
  - Expected: Project #5 is displayed in filter

- [ ] **Test 5.2**: Open old URL format `?user_id=3`
  - Expected: Single user filter works
  - Expected: User #3 is displayed in filter

- [ ] **Test 5.3**: Mix old and new formats `?project_id=5&user_ids=3,4`
  - Expected: New format (user_ids) takes precedence
  - Expected: Old format (project_id) is used for project

### 6. URL State & Sharing

- [ ] **Test 6.1**: Apply filters and copy URL
  - Expected: URL contains all filter parameters
  - Open URL in new tab/window
  - Expected: Same filters are applied
  - Expected: Same tasks are displayed

- [ ] **Test 6.2**: Use browser back button after filtering
  - Expected: Previous filter state is restored
  - Expected: Tasks update accordingly

### 7. Export Functionality (Tasks View)

- [ ] **Test 7.1**: Apply multi-select filters, then click "Export"
  - Expected: Export URL includes `project_ids` and `assigned_to_ids` parameters
  - Expected: Exported CSV contains only filtered tasks

### 8. Mobile Responsiveness

- [ ] **Test 8.1**: Open on mobile device or narrow browser window
  - Expected: Dropdowns are touch-friendly
  - Expected: Checkboxes are large enough to tap
  - Expected: Dropdown doesn't overflow screen
  - Expected: Search box is usable

### 9. Accessibility

- [ ] **Test 9.1**: Keyboard navigation
  - Tab to dropdown button
  - Press Enter/Space to open
  - Expected: Dropdown opens
  - Tab through checkboxes
  - Expected: Focus is visible
  - Press Space to toggle checkboxes
  - Expected: Checkboxes toggle

- [ ] **Test 9.2**: Screen reader compatibility
  - Expected: Button has `aria-haspopup="listbox"`
  - Expected: Button has `aria-expanded` attribute
  - Expected: Checkboxes have `aria-label` attributes
  - Expected: Dropdown has `role="listbox"`

### 10. Edge Cases

- [ ] **Test 10.1**: No projects available
  - Expected: Dropdown shows "No items available"
  - Expected: No errors in console

- [ ] **Test 10.2**: No users available
  - Expected: Similar to 10.1

- [ ] **Test 10.3**: Select all items, then deselect all
  - Expected: Shows all tasks (no filter applied)
  - Expected: URL parameters are empty or removed

- [ ] **Test 10.4**: Click outside dropdown while open
  - Expected: Dropdown closes
  - Expected: Changes are NOT applied (must click Apply)

- [ ] **Test 10.5**: Rapid filter changes
  - Expected: AJAX requests are debounced (Tasks view)
  - Expected: No race conditions
  - Expected: Final state matches last selection

### 11. Performance

- [ ] **Test 11.1**: Select 10+ projects
  - Expected: Filtering completes in < 2 seconds
  - Expected: No browser lag

- [ ] **Test 11.2**: Filter with 100+ tasks
  - Expected: Results display smoothly
  - Expected: No noticeable performance degradation

### 12. Integration with Other Filters (Tasks View)

- [ ] **Test 12.1**: Combine multi-select with status filter
  - Expected: Both filters work together
  - Expected: Tasks match all criteria

- [ ] **Test 12.2**: Combine multi-select with priority filter
  - Expected: Both filters work together

- [ ] **Test 12.3**: Combine multi-select with search
  - Expected: Both filters work together
  - Expected: Search is case-insensitive

- [ ] **Test 12.4**: Combine multi-select with "Overdue only" checkbox
  - Expected: Both filters work together

## Automated Test Results

Run `python test_multiselect_filters.py` to execute automated tests:

```
Parse IDs: ✓ PASSED
SQLAlchemy Filters: ✓ PASSED
URL Parameters: ✓ PASSED
Backward Compatibility: ✓ PASSED
```

## Known Limitations

1. **Project-Specific Kanban Columns**: When multiple projects are selected in Kanban view, only global columns are used (not project-specific columns).

2. **Export Format**: Export uses comma-separated IDs in URL parameters, which may have length limitations for very large selections.

## Browser Compatibility

Tested on:
- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)

## Reporting Issues

If you encounter any issues during testing, please report them with:
1. Browser and version
2. Steps to reproduce
3. Expected behavior
4. Actual behavior
5. Console errors (if any)
6. Screenshots (if applicable)

## Implementation Details

### Backend Changes
- **Kanban Route** (`app/routes/kanban.py`): Added `parse_ids()` function to handle both single and multi-select parameters
- **Tasks Route** (`app/routes/tasks.py`): Similar `parse_ids()` function added
- **Task Service** (`app/services/task_service.py`): Updated to accept lists of IDs and use SQLAlchemy `.in_()` filter

### Frontend Changes
- **Multi-Select Component** (`app/templates/components/multi_select.html`): New reusable Jinja2 macro with JavaScript
- **Kanban Template** (`app/templates/kanban/board.html`): Replaced dropdowns with multi-select component
- **Tasks Template** (`app/templates/tasks/list.html`): Replaced dropdowns with multi-select component
- **Tasks AJAX Handler**: Updated to listen for changes on hidden inputs from multi-select

### URL Parameters
- **Old Format**: `?project_id=5&user_id=3` (still supported)
- **New Format**: `?project_ids=1,2,3&user_ids=4,5,6`
- **Mixed Format**: `?project_id=5&user_ids=4,5` (new format takes precedence)
