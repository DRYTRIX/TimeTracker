# User Guide: Duplicating Time Entries

## What is Time Entry Duplication?

Time Entry Duplication allows you to quickly copy an existing time entry with all its details, saving you time when logging similar work. Instead of re-entering project, task, notes, and tags, you can duplicate a previous entry and just adjust the times.

## When Should You Use Duplication?

Time entry duplication is perfect for:
- **Daily recurring tasks**: Code reviews, standup meetings, email management
- **Similar work across days**: Project documentation, testing, client calls
- **Consistent activities**: Training sessions, administrative work, research
- **Template-like entries**: When you have a standard way of logging certain types of work

## How to Duplicate a Time Entry

### From the Dashboard

1. **Navigate to Dashboard**: Go to your main dashboard
2. **Find the Entry**: Locate the time entry you want to duplicate in the "Recent Entries" table
3. **Click Duplicate**: Click the blue copy icon (<i class="fas fa-copy"></i>) in the Actions column
4. **Adjust Times**: The form opens with all fields pre-filled. Set your new start and end times
5. **Modify if Needed**: Change any other details (project, task, notes, tags, billable status)
6. **Submit**: Click "Log Time" to create your duplicated entry

### From the Edit Entry Page

1. **Open Entry**: Click the edit icon (<i class="fas fa-edit"></i>) on any time entry
2. **Click Duplicate**: On the edit page, click the "Duplicate" button next to "Back"
3. **Adjust Times**: Set your new start and end times in the form
4. **Modify if Needed**: Update any fields as necessary
5. **Submit**: Click "Log Time" to create your duplicated entry

## What Gets Copied?

When you duplicate an entry, these fields are automatically filled in:

✅ **Project** - Same project as original
✅ **Task** - Same task (if the original had one)
✅ **Notes** - Same description/notes
✅ **Tags** - Same tags (comma-separated)
✅ **Billable Status** - Same billable flag

⚠️ **Times are NOT copied** - You must set new start and end times

## Example Workflows

### Example 1: Daily Code Review

**Scenario**: You review code every morning from 9:00 AM to 10:00 AM.

1. Find yesterday's code review entry on your dashboard
2. Click the duplicate icon (<i class="fas fa-copy"></i>)
3. Change start time to today at 9:00 AM
4. Change end time to today at 10:00 AM
5. Click "Log Time"
6. Done! Entry created in 10 seconds

### Example 2: Weekly Team Meeting

**Scenario**: Your team has a meeting every Monday at 2:00 PM.

1. Find last week's team meeting entry
2. Click duplicate
3. Update the date to this Monday
4. Adjust times if the meeting duration changed
5. Update notes with this week's agenda (optional)
6. Submit

### Example 3: Client Work Across Projects

**Scenario**: You do similar consultation work for multiple clients.

1. Find a consultation entry from Client A's project
2. Click duplicate
3. Change the project to Client B
4. Adjust times to when you worked with Client B
5. Update notes with client-specific details
6. Submit

## Understanding the Information Banner

When duplicating, you'll see a blue information banner at the top:

```
ℹ️ Duplicating entry: Project Name - Task Name
   Original: 2024-01-14 09:00 to 2024-01-14 11:00 (02:00:00)
```

This helps you verify you're duplicating the correct entry and shows:
- The project and task you're copying from
- The original time range and duration
- A reminder that you're creating a copy

## Tips and Best Practices

### 🎯 Quick Duplication Tips
- **Keep a Reference Entry**: Create a "template" entry for recurring work and duplicate it each time
- **Use Clear Tags**: Consistent tags on original entries make duplicates more useful
- **Regular Work**: Use duplication for any task you do more than once a week
- **Batch Similar Work**: Duplicate one entry multiple times for the same type of work

### ⚡ Speed Up Your Workflow
1. **From Dashboard**: Quickest access - duplicate right from the main view
2. **Keyboard Navigation**: Use Tab to move between form fields quickly
3. **Copy Similar Times**: If work takes roughly the same time, just adjust the date
4. **Update Notes Briefly**: Don't feel obligated to rewrite notes - adjust what changed

### 🔒 What to Check Before Duplicating
- ✅ The original entry has the correct project
- ✅ Tags and notes are still relevant
- ✅ Billable status is appropriate
- ✅ Task assignment (if any) is correct

## Frequently Asked Questions

### Q: Can I duplicate someone else's time entry?
**A**: No, you can only duplicate your own entries. Administrators can duplicate any entry.

### Q: What if the project is now inactive?
**A**: You can still view the duplication form, but you'll need to select an active project before submitting.

### Q: Can I duplicate an entry to multiple dates at once?
**A**: Not directly with duplication. For that, use the **Bulk Entry** feature instead. Duplication is for single entries.

### Q: Will the duplicate have the same ID as the original?
**A**: No, each entry gets a unique ID. The duplicate is a completely separate entry.

### Q: What happens to the original entry?
**A**: Nothing. The original entry remains unchanged. Duplication creates a new entry with copied data.

### Q: Can I duplicate an active (running) timer?
**A**: Yes, but you'll need to set both start and end times for the duplicate since it will be a completed entry.

### Q: How is this different from Time Entry Templates?
**A**: 
- **Duplication**: Copy a specific past entry (one-time action)
- **Templates**: Create reusable templates for future use (permanent resource)

Use templates for regular recurring work, duplication for quick one-off copies.

### Q: Can I undo a duplication?
**A**: After creating the duplicate, you can delete it like any other entry. There's no automatic undo, but deletion is straightforward.

## Troubleshooting

### Duplicate Button Not Visible
- **Check ownership**: You can only see duplicate buttons on your own entries
- **Refresh the page**: Sometimes the page needs to reload
- **Try from edit page**: The button also appears on the edit entry page

### Task Not Selected After Duplicating
- **Wait for load**: Tasks load dynamically; give it a moment
- **Re-select manually**: If it doesn't auto-select, just choose from the dropdown

### Form Submission Fails
- **Check required fields**: Start time, end time, and project must be filled
- **Verify time range**: End time must be after start time
- **Check project status**: The selected project must be active

## Related Features

- **Manual Entry**: Create entries from scratch without duplication
- **Bulk Entry**: Create multiple entries across a date range
- **Time Entry Templates**: Save reusable templates for common work
- **Edit Entry**: Modify existing entries

## Need More Help?

- Check the [Time Entry Duplication Technical Documentation](../features/TIME_ENTRY_DUPLICATION.md)
- Review the [Manual Entry Guide](./MANUAL_TIME_ENTRY.md) for form field details
- Contact your system administrator for specific questions

---

**Last Updated**: October 23, 2024
**Feature Version**: 1.0

