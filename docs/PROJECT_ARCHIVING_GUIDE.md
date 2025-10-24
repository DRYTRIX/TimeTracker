# Project Archiving Guide

## Overview

The Project Archiving feature provides a comprehensive solution for organizing completed, cancelled, or inactive projects in TimeTracker. This guide explains how to use the archiving system effectively.

## Table of Contents

1. [What is Project Archiving?](#what-is-project-archiving)
2. [When to Archive Projects](#when-to-archive-projects)
3. [Archiving a Single Project](#archiving-a-single-project)
4. [Bulk Archiving](#bulk-archiving)
5. [Viewing Archived Projects](#viewing-archived-projects)
6. [Unarchiving Projects](#unarchiving-projects)
7. [Archive Metadata](#archive-metadata)
8. [Restrictions on Archived Projects](#restrictions-on-archived-projects)
9. [API Reference](#api-reference)
10. [Best Practices](#best-practices)

---

## What is Project Archiving?

Project archiving allows you to hide completed or inactive projects from your active project lists while preserving all historical data. Archived projects:

- Are removed from active project dropdowns
- Cannot have new time entries added
- Retain all existing time entries and data
- Can be filtered and viewed separately
- Can be unarchived if needed
- Store metadata about when, why, and by whom they were archived

---

## When to Archive Projects

Consider archiving a project when:

- ✅ The project is completed
- ✅ The client contract has ended
- ✅ The project has been cancelled
- ✅ Work is on indefinite hold
- ✅ The maintenance period has ended
- ✅ You want to declutter your active project list

**Do NOT archive projects that:**
- ❌ Are temporarily paused (use "Inactive" status instead)
- ❌ May need time tracking in the near future
- ❌ Are awaiting client feedback
- ❌ Have ongoing maintenance work

---

## Archiving a Single Project

### Step-by-Step Process

1. **Navigate to the Project**
   - Go to **Projects** in the main navigation
   - Find the project you want to archive
   - Click **View** to open the project details

2. **Click Archive Button**
   - On the project details page, click the **Archive** button (visible to administrators only)
   - You'll be taken to the archive confirmation page

3. **Provide Archive Reason (Optional but Recommended)**
   - Enter a reason for archiving in the text field
   - This helps with future reference and organization
   - Use the **Quick Select** buttons for common reasons:
     - Project Completed
     - Contract Ended
     - Cancelled
     - On Hold
     - Maintenance Ended
   - Or type a custom reason

4. **Confirm Archive**
   - Click **Archive Project** to confirm
   - The project will be archived immediately
   - You'll be redirected to the archived projects list

### Example Archive Reasons

```
✓ "Project delivered on 2025-01-15. Client satisfied with results."
✓ "Annual contract ended. Client chose not to renew."
✓ "Project cancelled by client due to budget constraints."
✓ "Website maintenance complete. No further updates planned."
✓ "Internal tool - replaced with new system."
```

---

## Bulk Archiving

When you need to archive multiple projects at once:

### Using Bulk Archive

1. **Navigate to Projects List**
   - Go to **Projects** → **List All Projects**

2. **Select Projects**
   - Check the boxes next to projects you want to archive
   - Or click **Select All** to select all visible projects

3. **Open Bulk Actions Menu**
   - Click **Bulk Actions (N)** button (where N is the number selected)
   - Select **Archive** from the dropdown

4. **Enter Bulk Archive Reason**
   - A modal will appear
   - Enter a reason that applies to all selected projects
   - Or use one of the quick select buttons
   - Click **Archive** to confirm

5. **Confirmation**
   - All selected projects will be archived with the same reason
   - You'll see a success message with the count

### Bulk Archive Tips

- You can archive up to 100 projects at once
- All selected projects will receive the same archive reason
- The current user will be recorded as the archiver for all projects
- Projects with active timers cannot be archived (stop timers first)

---

## Viewing Archived Projects

### Filter Archived Projects

1. **Navigate to Projects List**
   - Go to **Projects** in the main navigation

2. **Apply Archive Filter**
   - In the filter section, select **Status**: **Archived**
   - Click **Filter**

3. **View Archived Project List**
   - All archived projects will be displayed
   - The list shows:
     - Project name and client
     - Archive status badge
     - Budget and billing information
     - Quick actions

### Viewing Individual Archived Project

When viewing an archived project's details page, you'll see:

**Archive Information Section:**
- **Archived on**: Date and time of archiving
- **Archived by**: User who archived the project
- **Reason**: Why the project was archived

All historical data remains accessible:
- Time entries
- Tasks
- Project costs
- Extra goods
- Comments
- Budget information

---

## Unarchiving Projects

If you need to reactivate an archived project:

### Unarchive Process

1. **Navigate to Archived Projects**
   - Go to **Projects** with **Status**: **Archived** filter

2. **Open Project Details**
   - Click **View** on the project you want to unarchive

3. **Click Unarchive Button**
   - Click the **Unarchive** button (administrators only)
   - Confirm the action in the dialog

4. **Project Reactivated**
   - The project status changes to **Active**
   - Archive metadata is cleared
   - The project appears in active lists again
   - Time tracking can resume

**Note**: Unarchiving a project:
- Removes all archive metadata (reason, date, user)
- Sets the project status to "active"
- Makes the project available for time tracking
- Preserves all historical data

---

## Archive Metadata

Each archived project stores three pieces of metadata:

### 1. Archived At (Timestamp)

- **Type**: Date and time
- **Timezone**: UTC
- **Purpose**: Track when the project was archived
- **Displayed**: Yes (in project details)
- **Example**: "2025-10-24 14:30:00"

### 2. Archived By (User)

- **Type**: User reference
- **Purpose**: Track who archived the project
- **Displayed**: Yes (shows username or full name)
- **Note**: If user is deleted, this field may show "Unknown"

### 3. Archived Reason (Text)

- **Type**: Free text (optional)
- **Max Length**: Unlimited
- **Purpose**: Document why the project was archived
- **Displayed**: Yes (in dedicated section)
- **Can include**: Multi-line text, special characters, emojis

### Viewing Metadata

Archive metadata is displayed on:
- Project details page (Archive Information section)
- API responses (`to_dict()` method)
- Activity logs
- Export reports

---

## Restrictions on Archived Projects

### What You CANNOT Do with Archived Projects

❌ **Time Tracking**
- Cannot start new timers
- Cannot create manual time entries
- Cannot create bulk time entries
- Error message: "Cannot start timer for an archived project. Please unarchive the project first."

❌ **Project Dropdown**
- Archived projects don't appear in:
  - Timer start modal
  - Manual entry forms
  - Bulk entry forms
  - Quick timer buttons

### What You CAN Do with Archived Projects

✅ **View Data**
- View project details
- Access time entry history
- See tasks and their status
- Review project costs
- Read comments

✅ **Generate Reports**
- Include in time reports
- Generate invoices from historical data
- Export time entries
- View analytics

✅ **Admin Actions**
- Unarchive the project
- Edit project details (after unarchiving)
- Delete the project (if no time entries)
- Change client assignment

---

## API Reference

### Archive a Project

```python
# Python/Flask
project = Project.query.get(project_id)
project.archive(user_id=current_user.id, reason="Project completed")
db.session.commit()
```

```javascript
// JavaScript/API
fetch('/projects/123/archive', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': csrfToken
    },
    body: new URLSearchParams({
        'reason': 'Project completed successfully'
    })
});
```

### Unarchive a Project

```python
# Python/Flask
project = Project.query.get(project_id)
project.unarchive()
db.session.commit()
```

```javascript
// JavaScript/API
fetch('/projects/123/unarchive', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrfToken
    }
});
```

### Get Archive Status

```python
# Check if project is archived
if project.is_archived:
    print(f"Archived on: {project.archived_at}")
    print(f"Archived by: {project.archived_by_user.username}")
    print(f"Reason: {project.archived_reason}")
```

### Project to Dictionary

```python
# Get project data including archive metadata
project_dict = project.to_dict()

# Access archive fields
is_archived = project_dict['is_archived']
archived_at = project_dict['archived_at']  # ISO format string or None
archived_by = project_dict['archived_by']  # User ID or None
archived_reason = project_dict['archived_reason']  # Text or None
```

### Filter Archived Projects

```python
# Get all archived projects
archived_projects = Project.query.filter_by(status='archived').all()

# Get projects archived by specific user
user_archived = Project.query.filter_by(
    status='archived',
    archived_by=user_id
).all()

# Get projects archived in date range
from datetime import datetime, timedelta
week_ago = datetime.utcnow() - timedelta(days=7)
recently_archived = Project.query.filter(
    Project.status == 'archived',
    Project.archived_at >= week_ago
).all()
```

### Bulk Archive

```http
POST /projects/bulk-status-change
Content-Type: application/x-www-form-urlencoded

project_ids[]=1&project_ids[]=2&project_ids[]=3&new_status=archived&archive_reason=Bulk+archive+reason
```

---

## Best Practices

### 1. Always Provide Archive Reasons

**Good Practice:**
```
✓ Document WHY the project was archived
✓ Include relevant dates (completion, cancellation)
✓ Mention key outcomes or decisions
✓ Reference client communications if applicable
```

**Example Good Reasons:**
- "Project completed on schedule. Final invoice sent and paid."
- "Client contract ended Q4 2024. No renewal planned."
- "Cancelled due to client budget cuts. 75% of work completed."

### 2. Review Before Archiving

Before archiving, verify:
- [ ] All time entries are logged
- [ ] Final invoice generated (if applicable)
- [ ] All outstanding tasks are resolved or noted
- [ ] Client deliverables are complete
- [ ] No active timers are running
- [ ] Team members are notified

### 3. Use Bulk Archive Strategically

Bulk archive is ideal for:
- End-of-year cleanup
- Multiple projects from same client (contract ended)
- Maintenance projects after completion
- Internal projects that are no longer needed

### 4. Regular Archive Audits

Periodically review archived projects:
- **Monthly**: Review recently archived projects
- **Quarterly**: Audit archive reasons for completeness
- **Yearly**: Consider permanent deletion of very old projects (backup first!)

### 5. Archive vs. Inactive

Use the right status:

**Archive when:**
- Project is completely finished
- No future work expected
- Want to hide from all lists

**Inactive when:**
- Temporarily paused
- Waiting for client
- May resume in near future
- Want to keep in lists but marked as not active

### 6. Unarchive Sparingly

Only unarchive if:
- New work is required on the project
- Contract is renewed
- Client requests additional features
- You need to add historical entries

Consider creating a new project instead if:
- It's a new phase/version
- Significant time has passed
- Scope has changed dramatically

---

## Troubleshooting

### Cannot Start Timer on Archived Project

**Problem**: Error message when starting timer

**Solution**:
1. Check if project is archived (Projects → Filter: Archived)
2. Unarchive the project if work needs to continue
3. Or create a new project for new work

### Cannot Find Archived Project in Dropdown

**Problem**: Archived project doesn't appear in timer dropdown

**Solution**: This is expected behavior. Archived projects are hidden from active lists. To work on an archived project, unarchive it first.

### Lost Archive Reason After Unarchive

**Problem**: Archive reason is gone after unarchiving

**Solution**: This is by design. Archive metadata is cleared when unarchiving. If you need to preserve the reason:
1. Copy the archive reason before unarchiving
2. Add it to project description or comments
3. Or take a screenshot of the archive information

### Bulk Archive Not Working

**Problem**: Some projects not archived in bulk operation

**Solution**:
1. Check if you have admin permissions
2. Ensure no projects have active timers
3. Verify projects are selected (checkboxes checked)
4. Check for error messages in the flash notifications

---

## Migration from Old System

If you're upgrading from a version without archive metadata:

### What Happens to Existing Archived Projects?

- Existing archived projects retain their "archived" status
- Archive metadata fields will be NULL:
  - `archived_at`: NULL
  - `archived_by`: NULL
  - `archived_reason`: NULL
- Projects still function normally
- You can add archive reasons by:
  1. Unarchiving the project
  2. Re-archiving with a reason

### Manual Migration (Optional)

To add metadata to existing archived projects:

```python
# Example migration script
from app import db
from app.models import Project
from datetime import datetime

# Get all archived projects without metadata
archived_projects = Project.query.filter(
    Project.status == 'archived',
    Project.archived_at.is_(None)
).all()

# Set archive timestamp to created_at or updated_at
for project in archived_projects:
    project.archived_at = project.updated_at or project.created_at
    project.archived_reason = "Migrated from old system"
    # Leave archived_by as NULL if you don't know who archived it

db.session.commit()
```

---

## Database Schema

For developers and database administrators:

### New Fields in `projects` Table

```sql
ALTER TABLE projects 
ADD COLUMN archived_at DATETIME NULL,
ADD COLUMN archived_by INTEGER NULL,
ADD COLUMN archived_reason TEXT NULL,
ADD FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE SET NULL,
ADD INDEX ix_projects_archived_at (archived_at);
```

### Field Specifications

| Field | Type | Nullable | Index | Default | Foreign Key |
|-------|------|----------|-------|---------|-------------|
| `archived_at` | DATETIME | Yes | Yes | NULL | - |
| `archived_by` | INTEGER | Yes | No | NULL | users(id) ON DELETE SET NULL |
| `archived_reason` | TEXT | Yes | No | NULL | - |

---

## Support and Feedback

If you encounter issues with project archiving:

1. Check this documentation
2. Review the [Troubleshooting](#troubleshooting) section
3. Contact your system administrator
4. Report bugs via GitHub Issues

---

**Document Version**: 1.0  
**Last Updated**: October 24, 2025  
**TimeTracker Version**: 2.0+

