# Client Notes Feature

## Overview

The **Client Notes** feature allows you to add internal notes about your clients. These notes are completely private and only visible to your team, not to clients. This is perfect for tracking important client information, preferences, special requirements, or any other internal details you need to remember.

---

## Key Features

### 📝 Internal Note Taking
- Add unlimited notes to any client
- Notes are completely internal and never visible to clients
- Rich text formatting with line breaks preserved

### ⭐ Important Notes
- Mark specific notes as "important" for quick identification
- Important notes are visually highlighted with a distinct indicator
- Toggle importance status with a single click

### 👥 Multi-User Support
- Each note tracks who created it and when
- View the author and timestamp for every note
- Edit history shows when notes were last modified

### 🔒 Access Control
- Users can edit and delete their own notes
- Administrators can edit and delete any note
- All actions are logged for audit purposes

---

## How to Use

### Adding a Note

1. Navigate to a client's detail page by clicking on the client name
2. Scroll down to the **Internal Notes** section
3. Click the **Add Note** button
4. Enter your note content in the text area
5. Optionally, check **Mark as important** for critical information
6. Click **Save Note**

### Viewing Notes

All notes for a client are displayed in the **Internal Notes** section on the client detail page:

- Notes are shown in reverse chronological order (newest first)
- Important notes are highlighted with an amber left border and a star icon
- Each note displays:
  - Author's name
  - Creation date and time
  - Edit indicator if the note was modified
  - Note content

### Editing a Note

1. Locate the note you want to edit
2. Click the **Edit** link next to the note
3. Modify the content and/or importance flag
4. Click **Save Changes**

> **Note:** You can only edit notes you created, unless you're an administrator.

### Marking Notes as Important

You can toggle the importance of a note in two ways:

**Method 1: Quick Toggle**
- Click the **Mark Important** or **Unmark** button next to any note
- The page will refresh automatically with the updated status

**Method 2: While Editing**
- Open the note for editing
- Check or uncheck the **Mark as important** checkbox
- Save your changes

### Deleting a Note

1. Locate the note you want to delete
2. Click the **Delete** button next to the note
3. Confirm the deletion when prompted

> **Warning:** Deleting a note is permanent and cannot be undone.

---

## Use Cases

### Client Preferences
```
Example: "Client prefers morning meetings (before 11 AM). 
Doesn't like phone calls - always use email."
```

### Special Requirements
```
Example: "All invoices must be sent to finance@client.com 
in addition to the main contact. Net 45 payment terms."
```

### Project History
```
Example: "Previous project had scope creep issues. 
Make sure to clearly define deliverables upfront."
```

### Communication Notes
```
Example: "Decision maker is Jane (CEO), but contact person 
is Bob (Project Manager). Include both on important emails."
```

---

## API Endpoints

For developers integrating with TimeTracker, the following API endpoints are available:

### List Client Notes
```http
GET /api/clients/{client_id}/notes
```

**Query Parameters:**
- `order_by_important` (boolean, optional): Order important notes first

**Response:**
```json
{
  "success": true,
  "notes": [
    {
      "id": 1,
      "content": "Example note",
      "client_id": 5,
      "client_name": "Acme Corp",
      "user_id": 2,
      "author": "john.doe",
      "author_name": "John Doe",
      "is_important": true,
      "created_at": "2025-10-24T10:30:00",
      "updated_at": "2025-10-24T10:30:00"
    }
  ]
}
```

### Get Single Note
```http
GET /api/client-notes/{note_id}
```

### Get Important Notes
```http
GET /api/client-notes/important
```

**Query Parameters:**
- `client_id` (integer, optional): Filter by specific client

### Get Recent Notes
```http
GET /api/client-notes/recent
```

**Query Parameters:**
- `limit` (integer, optional, default: 10): Number of notes to return

### Get User's Notes
```http
GET /api/client-notes/user/{user_id}
```

**Query Parameters:**
- `limit` (integer, optional): Number of notes to return

### Toggle Important Flag
```http
POST /clients/{client_id}/notes/{note_id}/toggle-important
```

**Response:**
```json
{
  "success": true,
  "is_important": true
}
```

---

## Database Schema

The client notes feature uses the following database table:

### `client_notes` Table

| Column        | Type      | Description                              |
|---------------|-----------|------------------------------------------|
| `id`          | Integer   | Primary key                              |
| `content`     | Text      | Note content (required)                  |
| `client_id`   | Integer   | Foreign key to `clients.id` (required)   |
| `user_id`     | Integer   | Foreign key to `users.id` (required)     |
| `is_important`| Boolean   | Important flag (default: false)          |
| `created_at`  | DateTime  | Creation timestamp                       |
| `updated_at`  | DateTime  | Last update timestamp                    |

**Indexes:**
- `ix_client_notes_client_id` on `client_id`
- `ix_client_notes_user_id` on `user_id`
- `ix_client_notes_created_at` on `created_at`
- `ix_client_notes_is_important` on `is_important`

**Relationships:**
- Notes are deleted when the associated client is deleted (CASCADE)
- Notes belong to a user (author) and a client

---

## Permissions

### Regular Users
- ✅ View all notes on clients they have access to
- ✅ Create new notes
- ✅ Edit their own notes
- ✅ Delete their own notes
- ✅ Toggle importance on their own notes
- ❌ Edit notes created by other users
- ❌ Delete notes created by other users

### Administrators
- ✅ All regular user permissions
- ✅ Edit any note
- ✅ Delete any note
- ✅ Toggle importance on any note

---

## Security & Privacy

### Internal Only
- Client notes are **never** exposed to clients
- Notes do not appear on invoices, reports, or any client-facing documents
- API endpoints require authentication

### Audit Trail
- All note actions (create, update, delete) are logged in the system event log
- Includes timestamp, user ID, and action details
- Can be reviewed by administrators for compliance

### Data Protection
- Notes are stored in the main database with the same security measures as other sensitive data
- Backup procedures include client notes
- Notes are included in data exports for compliance purposes

---

## Migration Guide

To enable the client notes feature on an existing TimeTracker installation:

### Step 1: Update Code
```bash
git pull origin main
```

### Step 2: Run Database Migration
```bash
# Using Flask-Migrate
flask db upgrade

# Or using Alembic directly
alembic upgrade head
```

### Step 3: Restart Application
```bash
# Docker
docker-compose restart

# Local development
flask run
```

### Verify Installation
1. Navigate to any client detail page
2. You should see the **Internal Notes** section at the bottom
3. Try adding a test note

---

## Troubleshooting

### Notes Section Not Visible

**Problem:** The Internal Notes section doesn't appear on the client page.

**Solution:**
1. Ensure you've run the latest database migration
2. Clear your browser cache
3. Check the browser console for JavaScript errors
4. Verify the user has permission to view clients

### Cannot Edit Notes

**Problem:** Edit button is missing or doesn't work.

**Solution:**
1. Verify you're logged in
2. Check that you're either the note's author or an administrator
3. Ensure JavaScript is enabled in your browser

### API Endpoints Return 404

**Problem:** API calls to note endpoints fail with 404.

**Solution:**
1. Verify the application has been restarted after update
2. Check that the `client_notes_bp` blueprint is registered in `app/__init__.py`
3. Review application logs for import errors

---

## Best Practices

### 1. Be Descriptive
Write clear, detailed notes that will be helpful months from now. Include:
- Context and background
- Specific dates if relevant
- Names of people involved
- Action items or follow-ups

### 2. Use Important Flag Wisely
Reserve the "important" flag for truly critical information:
- Legal or compliance requirements
- Financial terms and conditions
- Critical preferences or restrictions
- Emergency contact information

### 3. Keep Notes Updated
- Review and update notes periodically
- Archive or delete outdated information
- Add new notes when circumstances change

### 4. Maintain Professionalism
Remember that notes are:
- Potentially subject to legal discovery
- May be seen by other team members
- Part of your business records

Always write notes professionally and factually.

### 5. Use Notes for Team Communication
Notes are a great way to share knowledge:
- Document client quirks or preferences
- Share insights from client meetings
- Provide context for new team members
- Record decisions and their rationale

---

## Related Features

- **[Client Management](CLIENT_MANAGEMENT_README.md)** — Complete guide to managing clients
- **[Project Management](#)** — Link projects to clients
- **[Invoice System](INVOICE_FEATURE_README.md)** — Bill clients for your work
- **[Comment System](#)** — Add comments to projects and tasks

---

## Support

If you encounter issues with the Client Notes feature:

1. Check this documentation for solutions
2. Review the [Troubleshooting Guide](SOLUTION_GUIDE.md)
3. Search existing [GitHub Issues](https://github.com/yourusername/TimeTracker/issues)
4. Create a new issue with:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Screenshots if applicable
   - Browser and OS information

---

## Changelog

### Version 1.0.0 (2025-10-24)
- ✨ Initial release of Client Notes feature
- ✅ Create, read, update, delete operations
- ✅ Important flag functionality
- ✅ Multi-user support with permissions
- ✅ API endpoints
- ✅ Full test coverage
- ✅ Comprehensive documentation

---

## Contributing

Contributions to improve the Client Notes feature are welcome! Please:

1. Read the [Contributing Guide](CONTRIBUTING.md)
2. Check for existing issues or create a new one
3. Submit pull requests with:
   - Clear description of changes
   - Unit tests for new functionality
   - Updated documentation if needed

---

**[← Back to Documentation Home](README.md)**

