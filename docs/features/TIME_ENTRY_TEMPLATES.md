# Time Entry Notes Templates - Reusable Note Templates

## Overview

Time Entry Templates allow you to create reusable templates for frequently logged activities, saving time and ensuring consistency. This feature is particularly useful for recurring tasks like meetings, standups, client calls, or any activities you log regularly.

## Features

- **Quick-start templates** for common time entries
- **Pre-filled project, task, and notes** to reduce data entry
- **Default duration** settings for consistent time tracking
- **Tag templates** for better organization
- **Usage tracking** to see which templates you use most often
- **Billable/non-billable** defaults

## How to Use Time Entry Templates

### Creating a Template

1. Navigate to **Templates** from the main navigation menu
2. Click **"New Template"** or **"Create Your First Template"**
3. Fill in the template details:
   - **Template Name** (required): A descriptive name for the template (e.g., "Daily Standup", "Client Call")
   - **Project** (optional): The default project for this template
   - **Task** (optional): The default task within the project
   - **Default Duration** (optional): The typical duration in hours (e.g., 0.5 for 30 minutes, 1.5 for 90 minutes)
   - **Default Notes** (optional): Pre-filled notes that will appear when using the template
   - **Tags** (optional): Comma-separated tags for categorization
   - **Billable** (optional): Whether time entries from this template should be billable by default
4. Click **"Create Template"**

### Using a Template

There are two ways to use a template:

#### Method 1: From the Templates Page

1. Navigate to **Templates**
2. Find the template you want to use
3. Click the **"Use Template"** button
4. You'll be redirected to the manual time entry page with all fields pre-filled
5. Adjust the start and end times as needed
6. Click **"Log Time"** to create the entry

#### Method 2: Direct Link

Templates can be accessed directly via URL query parameters:
```
/timer/manual?template=<template_id>
```

### Editing a Template

1. Navigate to **Templates**
2. Find the template you want to edit
3. Click the **edit icon** (pencil)
4. Update the template details
5. Click **"Update Template"**

### Deleting a Template

1. Navigate to **Templates**
2. Find the template you want to delete
3. Click the **delete icon** (trash can)
4. Confirm the deletion in the dialog

## Template Details

Each template displays:

- **Template name** and optional description
- **Associated project** (if specified)
- **Associated task** (if specified)
- **Default duration** (if specified)
- **Default notes** (preview of first few lines)
- **Tags** (if specified)
- **Usage statistics**: How many times the template has been used
- **Last used**: When the template was last used

## Use Cases

### Daily Recurring Activities

Create templates for activities you do every day:
- **Daily Standup Meeting**: Project: "Internal", Duration: 0.25 hours (15 min)
- **Email Processing**: Project: "Administrative", Duration: 0.5 hours
- **Code Review**: Project: "Development", Notes: "Reviewed team pull requests"

### Client-Specific Templates

Create templates for regular client work:
- **Weekly Client Check-in**: Project: "Client A", Duration: 1 hour
- **Monthly Reporting**: Project: "Client B", Duration: 2 hours

### Task-Specific Templates

Create templates for specific types of work:
- **Bug Fixes**: Tags: "bug,development", Billable: Yes
- **Documentation**: Tags: "documentation,writing", Billable: No
- **Training**: Tags: "learning,training", Billable: No

## Best Practices

### Template Naming

- Use clear, descriptive names that indicate the activity
- Include the project name if you have templates for multiple projects
- Use consistent naming conventions (e.g., "Weekly [Activity]", "Monthly [Activity]")

### Default Duration

- Set realistic default durations based on historical data
- Use common increments (0.25, 0.5, 1.0, 2.0 hours)
- Leave duration empty if the activity varies significantly in length

### Default Notes

- Include structure or prompts for what to include
- Use bullet points or questions to guide note-taking
- Examples:
  ```
  - Topics discussed:
  - Action items:
  - Next steps:
  ```

### Tags

- Create a consistent tagging system across templates
- Use tags for reporting and filtering (e.g., "meeting", "development", "admin")
- Keep tags lowercase and short

### Maintenance

- Review your templates quarterly
- Delete unused templates to keep the list manageable
- Update templates as your work patterns change
- Check usage statistics to identify which templates are most valuable

## Template Management Tips

### Organizing Templates

Templates are sorted by last used date by default, so your most frequently used templates appear at the top. This makes it easy to access your most common activities quickly.

### Template Usage Tracking

The system tracks:
- **Usage count**: Total number of times the template has been used
- **Last used**: When the template was last applied

This data helps you:
- Identify your most common activities
- Clean up unused templates
- Understand your work patterns

### Sharing Templates

Templates are user-specific and cannot be shared directly with other users. However, admins can:
- Document standard templates in the team wiki
- Provide template "recipes" for common activities
- Export and import template configurations (if bulk operations are available)

## Technical Notes

### Template Application

When you use a template:
1. The template's usage count increments
2. The last used timestamp updates
3. All template fields populate the manual entry form
4. The template's default duration calculates the end time based on the current time
5. The template data is cleared from session storage after application

### Duration Handling

- Templates store duration in minutes internally
- The UI displays duration in hours (decimal format)
- When using a template, the duration is applied from the current time forward
- You can adjust start and end times manually after applying the template

### Data Persistence

- Templates are stored in the database and persist across sessions
- Template data is temporarily stored in browser sessionStorage during the "Use Template" flow
- SessionStorage is cleared after the template is applied to prevent accidental reuse

## API Access

Templates can be accessed programmatically via the API:

### List Templates
```http
GET /api/templates
```

Returns all templates for the authenticated user.

### Get Single Template
```http
GET /api/templates/<template_id>
```

Returns details for a specific template.

### Mark Template as Used
```http
POST /api/templates/<template_id>/use
```

Increments the usage count and updates the last used timestamp.

## Integration with Other Features

### Projects and Tasks

- Templates can reference specific projects and tasks
- When a project is archived or deleted, templates remain but show a warning
- Task selection is dynamic based on the selected project

### Time Entries

- Templates pre-fill time entry forms but don't create entries automatically
- All template fields can be modified before creating the time entry
- Templates don't override user preferences for billability

### Reporting

- Time entries created from templates are tracked like any other entry
- Tags from templates help with filtering and reporting
- Template usage statistics are separate from time entry reporting

## Troubleshooting

### Template Not Loading

If a template doesn't load when you click "Use Template":
1. Check browser console for JavaScript errors
2. Ensure JavaScript is enabled in your browser
3. Try refreshing the page and clicking the template again
4. Clear your browser's sessionStorage and try again

### Template Fields Not Pre-filling

If template fields don't pre-fill the form:
1. Verify the template has the fields populated
2. Check that the project/task still exist and are active
3. Ensure you're using a modern browser with sessionStorage support

### Template Not Appearing

If you created a template but don't see it:
1. Refresh the templates page
2. Check that you're logged in as the correct user (templates are user-specific)
3. Verify the template was created successfully (check for success message)

## Future Enhancements

Potential future features for templates:
- Template categories or folders for better organization
- Template sharing between users or teams
- Template cloning for quick creation of similar templates
- Bulk template import/export
- Template suggestions based on time entry patterns
- Template versioning and history

## Related Documentation

- [Time Tracking Guide](./TIME_TRACKING.md)
- [Manual Time Entry](./MANUAL_TIME_ENTRY.md)
- [Projects and Tasks](./PROJECTS_AND_TASKS.md)
- [Reporting and Analytics](./REPORTING.md)

## Support

If you encounter issues with Time Entry Templates:
1. Check this documentation for troubleshooting tips
2. Review the application logs for error messages
3. Contact your system administrator
4. Report bugs on the project's GitHub repository

