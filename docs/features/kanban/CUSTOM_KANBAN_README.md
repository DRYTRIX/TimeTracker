# Custom Kanban Board Columns - Quick Start Guide

## What's New?

Your TimeTracker application now supports **fully customizable kanban board columns**! You're no longer limited to just "To Do", "In Progress", "Review", and "Done". 

## Quick Start

### Step 1: Run the Migration

The kanban columns will be initialized automatically when you start the application. However, if you want to run the migration manually:

```bash
cd /path/to/TimeTracker
python migrations/migration_019_kanban_columns.py
```

Or simply restart your application - it will initialize the columns automatically.

### Step 2: Access Column Management (Admin Only)

1. Log in as an administrator
2. Navigate to any task page with a kanban board
3. Click the "Manage Columns" button (top-right of kanban board)
4. Or go directly to: `/kanban/columns`

### Step 3: Create Your First Custom Column

1. Click "Add Column"
2. Enter a name (e.g., "Testing", "Blocked", "Deployed")
3. Choose an icon from [Font Awesome](https://fontawesome.com/icons)
4. Pick a color
5. Optionally check "Mark as Complete State" if this column should complete tasks
6. Click "Create Column"

### Step 4: Customize Your Workflow

- **Reorder**: Drag columns using the ≡ icon
- **Edit**: Click the edit icon to change name, icon, or color
- **Hide**: Click the eye icon to temporarily hide a column
- **Delete**: Click the delete icon (only for custom columns with no tasks)

## Examples of Custom Columns

### Software Development Workflow
- 📋 **Backlog** (todo)
- 🚀 **In Progress** (in_progress)
- 🔍 **Code Review** (code_review)
- 🧪 **Testing** (testing)
- 🐛 **Bug Fix** (bug_fix)
- 🚢 **Deployed** (deployed) ✓ Complete
- ✅ **Done** (done) ✓ Complete

### Content Creation Workflow
- 💡 **Ideas** (ideas)
- ✍️ **Drafting** (drafting)
- 📝 **Editing** (editing)
- 👀 **Review** (review)
- 📢 **Published** (published) ✓ Complete

### Support Ticket Workflow
- 📬 **New** (new)
- 🔄 **In Progress** (in_progress)
- ⏸️ **Waiting** (waiting)
- ✅ **Resolved** (resolved) ✓ Complete
- 🔒 **Closed** (closed) ✓ Complete

## Key Features

### ✅ Unlimited Custom Columns
Create as many columns as you need for your workflow

### 🎨 Visual Customization
- Choose from Font Awesome icons (5000+ options)
- Pick Bootstrap colors (primary, success, warning, danger, etc.)
- Customize labels to match your terminology

### 🔒 Protected System Columns
- "To Do", "In Progress", and "Done" are protected
- Can customize their appearance
- Cannot be deleted to maintain data integrity

### ↕️ Drag-and-Drop Reordering
Easily reorder columns to match your workflow

### 👁️ Show/Hide Columns
Temporarily hide columns without deleting them

### 🎯 Complete State Marking
Mark columns that should automatically complete tasks

## Technical Details

### Default Columns

After initialization, you'll have these columns:
1. **To Do** (System) - Starting point for new tasks
2. **In Progress** (System) - Active work
3. **Review** - Optional review step
4. **Done** (System) - Completed tasks ✓

### System vs Custom Columns

**System Columns** (cannot be deleted):
- `todo` - To Do
- `in_progress` - In Progress  
- `done` - Done

**Custom Columns** (can be deleted if no tasks use them):
- Any columns you create
- Including the default "Review" column

### Column Properties

Each column has:
- **Key**: Unique identifier (e.g., `testing`, `blocked`)
- **Label**: Display name (e.g., "Testing", "Blocked")
- **Icon**: Font Awesome class (e.g., `fas fa-flask`)
- **Color**: Bootstrap color class (e.g., `warning`, `danger`)
- **Position**: Order on the board
- **Active**: Show/hide on board
- **Complete State**: Mark tasks as done

## API Integration

### Get All Active Columns

```bash
GET /api/kanban/columns
```

Response:
```json
{
  "columns": [
    {
      "id": 1,
      "key": "todo",
      "label": "To Do",
      "icon": "fas fa-list-check",
      "color": "secondary",
      "position": 0,
      "is_active": true
    }
  ]
}
```

### Reorder Columns

```bash
POST /api/kanban/columns/reorder
Content-Type: application/json

{
  "column_ids": [1, 3, 2, 4]
}
```

## Troubleshooting

### "Manage Columns" button not visible
- Make sure you're logged in as an administrator
- Only admins can manage kanban columns

### Cannot delete a column
- Check if any tasks are using that status
- Move those tasks to another column first
- System columns cannot be deleted

### Changes not appearing
- Refresh the page
- Clear browser cache if needed

### Column colors not showing
- Ensure you're using valid Bootstrap color classes
- Valid colors: primary, secondary, success, danger, warning, info, dark

## Need Help?

- See `KANBAN_CUSTOMIZATION.md` for detailed documentation
- See `IMPLEMENTATION_SUMMARY.md` for technical details
- Check the column management page for inline help

## Rollback

If you need to rollback this feature:

```bash
cd migrations
python migration_019_kanban_columns.py downgrade
```

Then restart the application.

## Enjoy Your Custom Workflow! 🎉

You now have a flexible kanban board that adapts to YOUR workflow, not the other way around!

