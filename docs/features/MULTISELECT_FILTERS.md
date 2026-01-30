# Multi-Select Filters Feature

## Overview
Multi-select filter functionality for Kanban and Tasks views, allowing users to filter by multiple projects and/or multiple users simultaneously.

## Issue Reference
- **GitHub Issue**: [#464](https://github.com/DRYTRIX/TimeTracker/issues/464)
- **Status**: ✅ Implemented
- **Date**: January 30, 2026

## Feature Description

### Before
Users could only:
- View all projects/users
- View a single project/user at a time

### After
Users can now:
- Select multiple specific projects to view
- Select multiple specific users to view
- Combine project and user filters
- Use "All" to clear filters quickly

## User Interface

### Multi-Select Component
Each filter dropdown includes:
- **Checkbox list**: All available items with checkboxes
- **Search box**: Filter items by name (appears when >5 items)
- **"All" checkbox**: Select/deselect all items at once
- **Selection count**: Shows "Selected: X" in the button
- **Clear button**: Quickly deselect all items
- **Apply button**: Apply the selected filters

### Kanban View
Location: `/kanban`
- Project filter (top right)
- Assigned To filter (top right)
- Full page reload on filter change

### Tasks View
Location: `/tasks`
- Project filter (in filter panel)
- Assigned To filter (in filter panel)
- AJAX filtering (no page reload)

## Technical Implementation

### URL Parameters

#### New Format (Multi-Select)
```
/kanban?project_ids=1,2,3&user_ids=4,5,6
/tasks?project_ids=1,2,3&assigned_to_ids=4,5,6
```

#### Old Format (Still Supported)
```
/kanban?project_id=5&user_id=3
/tasks?project_id=5&assigned_to=3
```

### Backend Logic

#### Parameter Parsing
```python
def parse_ids(param_name):
    """Parse comma-separated IDs or single ID into a list"""
    # Try multi-select parameter first
    multi_param = request.args.get(param_name + 's', '').strip()
    if multi_param:
        return [int(x.strip()) for x in multi_param.split(',') if x.strip()]
    # Fall back to single parameter
    single_param = request.args.get(param_name, type=int)
    if single_param:
        return [single_param]
    return []
```

#### Database Query
```python
# Before (single filter)
query = Task.query.filter_by(project_id=5)

# After (multi-select)
query = Task.query.filter(Task.project_id.in_([1, 2, 3]))
```

### Frontend Component

#### Usage Example
```jinja2
{% from "components/multi_select.html" import multi_select %}

{{ multi_select(
    field_name='project_ids',
    label='Project',
    items=projects,
    selected_ids=project_ids,
    item_id_attr='id',
    item_label_attr='name',
    placeholder='All Projects',
    show_search=True,
    form_id='filterForm'
) }}
```

## Files Modified

### Backend (3 files)
1. `app/routes/kanban.py` - Kanban route handler
2. `app/routes/tasks.py` - Tasks route handler  
3. `app/services/task_service.py` - Task service layer

### Frontend (4 files)
1. `app/templates/components/multi_select.html` - New component
2. `app/templates/kanban/board.html` - Kanban template
3. `app/templates/tasks/list.html` - Tasks template
4. `app/templates/tasks/_tasks_list.html` - Tasks list partial

## Key Features

✅ **Multi-select with checkboxes**  
✅ **Search functionality**  
✅ **"Select All" / "Clear All"**  
✅ **Backward compatibility**  
✅ **AJAX filtering (Tasks view)**  
✅ **URL state preservation**  
✅ **Mobile responsive**  
✅ **Dark mode support**  
✅ **Accessibility (ARIA, keyboard navigation)**  
✅ **Export with filters**  

## Testing

### Automated Tests
Run: `python tests/test_multiselect_filters.py`

Tests include:
- Parse IDs logic (8 tests)
- SQLAlchemy filters (5 tests)
- URL parameters (5 tests)
- Backward compatibility (3 tests)

**Status**: ✅ All 21 tests passed

### Manual Testing
See: [`docs/MULTISELECT_FILTERS_TESTING.md`](../MULTISELECT_FILTERS_TESTING.md)

Includes:
- 12 test scenario categories
- 40+ individual test cases
- Browser compatibility checklist
- Accessibility guidelines

## Known Limitations

1. **Kanban Project-Specific Columns**: When multiple projects are selected, only global Kanban columns are used (not project-specific columns).

2. **URL Length**: Very large selections (50+ items) may approach URL length limits in some browsers.

## Performance

- **Database**: Uses efficient `IN` clauses for filtering
- **AJAX**: Debounced requests (500ms for search, 100ms for dropdowns)
- **No N+1 queries**: Eager loading maintained
- **Impact**: Minimal - slightly larger HTML payload for component JavaScript

## Accessibility

- ✅ ARIA labels and roles
- ✅ Keyboard navigation (Tab, Space, Enter)
- ✅ Screen reader compatible
- ✅ Focus indicators
- ✅ Semantic HTML

## Browser Compatibility

Tested on:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile Safari (iOS)
- Chrome Mobile (Android)

## Usage Examples

### Example 1: View Two Specific Projects
1. Open Kanban or Tasks view
2. Click "Project" dropdown
3. Check "Project A" and "Project B"
4. Click "Apply"
5. View shows only tasks from those two projects

### Example 2: View Tasks for Your Team
1. Open Tasks view
2. Click "Assigned To" dropdown
3. Check team member names
4. Click "Apply"
5. View shows only tasks assigned to selected team members

### Example 3: Combine Filters
1. Select multiple projects
2. Select multiple users
3. Click "Apply" on both
4. View shows tasks that match BOTH criteria (AND logic)

### Example 4: Share Filtered View
1. Apply desired filters
2. Copy URL from browser address bar
3. Share URL with colleague
4. They see the same filtered view

## Future Enhancements

Potential improvements for future versions:
- Saved filter presets
- Recent selections memory
- Quick toggle shortcuts
- Visual tags/badges for selected items
- Drag to reorder selections

## Support

For issues or questions:
1. Check the [testing guide](../MULTISELECT_FILTERS_TESTING.md)
2. Review [GitHub issue #464](https://github.com/DRYTRIX/TimeTracker/issues/464)
3. Create a new issue with reproduction steps
