# Time Entry Templates

Time Entry Templates allow you to create reusable templates for frequently logged activities, saving time and ensuring consistency in your time tracking.

## Overview

Time Entry Templates help you:
- **Save time**: Start timers or create entries with pre-filled data
- **Ensure consistency**: Use the same project, task, and notes for recurring activities
- **Track patterns**: See which templates you use most often
- **Reduce errors**: Avoid manually entering the same information repeatedly

## Features

### Template Properties

Each template can include:
- **Name** (required): A descriptive name for quick identification
- **Description** (optional): Additional details about when to use this template
- **Project**: Pre-select a project for this activity
- **Task**: Pre-select a specific task within the project
- **Default Duration**: Set a standard duration in hours (e.g., 1.0, 0.5)
- **Default Notes**: Pre-fill notes/description for the time entry
- **Tags**: Comma-separated tags for categorization
- **Billable**: Whether time entries from this template should be billable

### Usage Tracking

Templates track:
- **Usage Count**: How many times the template has been used
- **Last Used**: When the template was last used
- Templates are automatically sorted by most recently used

## Using Templates

### Creating a Template

1. Navigate to **Templates** from the main navigation
2. Click **"New Template"**
3. Fill in the template details:
   - Enter a descriptive name
   - Select a project (and optionally a task)
   - Set default duration if desired
   - Add default notes and tags
4. Click **"Create Template"**

### Starting a Timer from a Template

There are three ways to use a template:

#### 1. From the Templates Page

1. Go to **Templates**
2. Click **"Use Template"** on any template card
3. You'll be redirected to create a time entry with pre-filled data

#### 2. From the Dashboard

1. On the dashboard, click **"Start Timer"**
2. In the start timer modal, you'll see a list of your recent templates
3. Click on any template to apply its data to the timer form
4. Click **"Start"** to begin tracking time

#### 3. Direct Timer Start

Some templates (those with a project assigned) have a direct "Start Timer" button that:
- Immediately starts a timer with the template's data
- Increments the template's usage count
- Takes you back to the dashboard

### Editing a Template

1. Navigate to **Templates**
2. Click the **edit icon** (pencil) on the template card
3. Update any fields as needed
4. Click **"Save Changes"**

### Deleting a Template

1. Navigate to **Templates**
2. Click the **delete icon** (trash) on the template card
3. Confirm the deletion

**Note**: Deleting a template does not affect any time entries that were created using it.

## Best Practices

### Naming Conventions

Use clear, descriptive names:
- ✅ Good: "Daily Standup", "Client Meeting - ProjectX", "Code Review"
- ❌ Poor: "Meeting", "Work", "Task1"

### When to Use Templates

Templates are ideal for:
- **Recurring meetings**: Daily standups, weekly syncs, client calls
- **Regular activities**: Code reviews, testing, documentation
- **Standard tasks**: Email correspondence, administrative work
- **Frequent projects**: Activities you do multiple times per week

### Organizing Templates

- Keep your template list focused (5-10 most-used templates)
- Delete or update templates you no longer use
- Use consistent naming and tagging schemes
- Review and clean up templates quarterly

### Duration Settings

- Leave duration blank for activities with variable length (start/stop timer)
- Set a duration for activities with predictable length (meetings, standup)
- Common durations: 0.25 (15 min), 0.5 (30 min), 1.0 (1 hour)

## API Integration

### Get All Templates

```http
GET /api/templates
```

Returns all templates for the current user.

**Response:**
```json
{
  "templates": [
    {
      "id": 1,
      "name": "Daily Standup",
      "project_id": 5,
      "project_name": "Internal",
      "task_id": 12,
      "task_name": "Team Meetings",
      "default_duration": 0.25,
      "default_notes": "Discussed progress and blockers",
      "tags": "meeting,standup",
      "billable": false,
      "usage_count": 45,
      "last_used_at": "2024-01-15T09:00:00Z"
    }
  ]
}
```

### Get Single Template

```http
GET /api/templates/{template_id}
```

Returns a specific template by ID.

### Mark Template as Used

```http
POST /api/templates/{template_id}/use
```

Records that the template was used (increments usage count and updates last_used_at).

## Troubleshooting

### Template Not Showing in Dashboard

- The dashboard shows only your 5 most recently used templates
- Visit the Templates page to see all your templates
- Use a template to move it to the top of the list

### Cannot Start Timer from Template

- Ensure the template has a project assigned
- Verify the project is active (not archived)
- Stop any active timers before starting a new one

### Template Data Not Pre-filling

- Check that you're using the correct method (template button, not manual form)
- Verify the template has the fields you expect filled in
- Try editing and re-saving the template

## Migration Notes

If you're upgrading to a version with time entry templates:

1. Templates are stored in a new `time_entry_templates` table
2. No migration is needed - the feature is additive
3. Templates are user-specific and don't affect existing time entries

## Related Features

- **[Time Tracking](TIME_TRACKING.md)**: Learn about manual time entries and timer
- **[Projects](PROJECTS.md)**: Understanding projects and their settings
- **[Tasks](TASKS.md)**: Using tasks within projects
- **[Reports](REPORTS.md)**: Analyzing your time data

## Tips and Tricks

### Quick Template Creation

Create templates from your most frequent activities by:
1. Track your time for a week
2. Review your time entries
3. Create templates for activities that appear 3+ times

### Template Chains

For complex workflows:
- Create separate templates for each phase
- Use consistent naming: "ProjectX - Phase 1", "ProjectX - Phase 2"
- This helps with reporting and analysis

### Keyboard Shortcuts

When using templates on the dashboard:
- The templates list is keyboard accessible
- Use Tab to navigate, Enter to select
- This speeds up your workflow significantly

## Frequently Asked Questions

**Q: Can I share templates with my team?**
A: Templates are currently user-specific. Each team member needs to create their own templates.

**Q: Will deleting a template affect my past time entries?**
A: No, time entries are independent once created. Deleting a template doesn't affect any existing time entries.

**Q: How many templates can I create?**
A: There's no hard limit, but we recommend keeping 10-20 active templates for ease of use.

**Q: Can I import/export templates?**
A: Currently, templates are managed through the UI. API support allows for programmatic creation if needed.

**Q: Do templates work with the mobile interface?**
A: Yes, templates are fully functional on mobile devices through the responsive web interface.

## Feedback

We'd love to hear how you're using time entry templates! If you have suggestions or encounter issues, please:
- Open an issue on GitHub
- Contact support
- Contribute improvements via pull request

