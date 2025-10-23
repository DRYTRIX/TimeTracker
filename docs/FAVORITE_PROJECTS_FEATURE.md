# Favorite Projects Feature

## Overview

The Favorite Projects feature allows users to mark frequently used projects as favorites for quick access. This feature enhances user productivity by providing easy access to the projects they work with most often.

## Features

- **Star Icon**: Each project in the project list has a star icon that can be clicked to favorite/unfavorite
- **Quick Filter**: Filter to show only favorite projects
- **Per-User**: Each user has their own set of favorite projects
- **Real-time Updates**: Favorite status updates immediately via AJAX
- **Status Awareness**: Favorites work with all project statuses (active, inactive, archived)

## User Guide

### Marking a Project as Favorite

1. Navigate to the Projects list page (`/projects`)
2. Find the project you want to favorite
3. Click the star icon (☆) next to the project name
4. The star will turn yellow/gold (★) indicating it's now a favorite

### Removing a Project from Favorites

1. Navigate to the Projects list page
2. Find the favorited project (marked with a gold star ★)
3. Click the star icon
4. The star will become hollow (☆) indicating it's no longer a favorite

### Filtering by Favorites

1. Navigate to the Projects list page
2. In the filters section, find the "Filter" dropdown
3. Select "Favorites Only"
4. Click "Filter"
5. The list will show only your favorite projects

### Combining Filters

You can combine the favorites filter with other filters:
- **Status Filter**: Show only active favorites, archived favorites, etc.
- **Client Filter**: Show favorites for a specific client
- **Search**: Search within your favorite projects

## Technical Implementation

### Database Schema

A new association table `user_favorite_projects` was created with the following structure:

```sql
CREATE TABLE user_favorite_projects (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (user_id, project_id)
);
CREATE INDEX ix_user_favorite_projects_user_id ON user_favorite_projects(user_id);
CREATE INDEX ix_user_favorite_projects_project_id ON user_favorite_projects(project_id);
```

### Model Relationships

#### User Model

New methods added to `app/models/user.py`:

- `add_favorite_project(project)`: Add a project to favorites
- `remove_favorite_project(project)`: Remove a project from favorites
- `is_project_favorite(project)`: Check if a project is favorited
- `get_favorite_projects(status='active')`: Get list of favorite projects

New relationship:
```python
favorite_projects = db.relationship('Project', 
                                   secondary='user_favorite_projects', 
                                   lazy='dynamic',
                                   backref=db.backref('favorited_by', lazy='dynamic'))
```

#### Project Model

New method added to `app/models/project.py`:

- `is_favorited_by(user)`: Check if project is favorited by a specific user

Updated method:
- `to_dict(user=None)`: Now includes `is_favorite` field when user is provided

### API Endpoints

#### POST /projects/<project_id>/favorite

Mark a project as favorite.

**Authentication**: Required  
**Method**: POST  
**Parameters**: None  
**Returns**: JSON response

**Example Request:**
```bash
curl -X POST https://timetracker.example.com/projects/123/favorite \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "Cookie: session=..."
```

**Example Response (Success):**
```json
{
  "success": true,
  "message": "Project added to favorites"
}
```

**Example Response (Error):**
```json
{
  "success": false,
  "message": "Project is already in favorites"
}
```

#### POST /projects/<project_id>/unfavorite

Remove a project from favorites.

**Authentication**: Required  
**Method**: POST  
**Parameters**: None  
**Returns**: JSON response

**Example Request:**
```bash
curl -X POST https://timetracker.example.com/projects/123/unfavorite \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "Cookie: session=..."
```

**Example Response (Success):**
```json
{
  "success": true,
  "message": "Project removed from favorites"
}
```

### Routes

#### GET /projects?favorites=true

List projects filtered by favorites.

**Authentication**: Required  
**Method**: GET  
**Parameters**: 
- `favorites`: "true" to show only favorites
- `status`: Filter by status (active/inactive/archived)
- `client`: Filter by client name
- `search`: Search in project name/description

**Example:**
```
GET /projects?favorites=true&status=active
```

### Frontend Implementation

#### JavaScript

The `toggleFavorite(projectId, button)` function handles the star icon clicks:

1. Performs optimistic UI update (changes star immediately)
2. Sends AJAX POST request to favorite/unfavorite endpoint
3. Reverts UI if request fails
4. Shows success/error message

#### UI Components

- **Star Icon**: FontAwesome icons (`fas fa-star` for favorited, `far fa-star` for not favorited)
- **Color Coding**: Yellow/gold for favorited, muted gray for not favorited
- **Filter Dropdown**: Added "Favorites Only" option to the filters form

## Migration

### Running the Migration

To add the favorite projects table to an existing database:

```bash
# Using Alembic
alembic upgrade head

# Or using the migration management script
python migrations/manage_migrations.py upgrade
```

### Rollback

To rollback the favorite projects feature:

```bash
alembic downgrade -1
```

## Activity Logging

The following activities are logged:

- `project.favorited`: When a user adds a project to favorites
- `project.unfavorited`: When a user removes a project from favorites

These activities can be viewed in:
- User activity logs
- System audit trail
- Analytics dashboards (if enabled)

## Testing

Comprehensive test coverage is provided in `tests/test_favorite_projects.py`:

### Test Categories

1. **Model Tests**: Testing the `UserFavoriteProject` model
2. **Method Tests**: Testing User and Project model methods
3. **Route Tests**: Testing API endpoints
4. **Filtering Tests**: Testing the favorites filter
5. **Relationship Tests**: Testing cascade delete behavior
6. **Smoke Tests**: End-to-end workflow tests

### Running Tests

```bash
# Run all favorite projects tests
pytest tests/test_favorite_projects.py -v

# Run specific test class
pytest tests/test_favorite_projects.py::TestUserFavoriteProjectModel -v

# Run with coverage
pytest tests/test_favorite_projects.py --cov=app.models --cov=app.routes -v
```

## Performance Considerations

### Database Indexes

The feature includes indexes on both `user_id` and `project_id` columns in the `user_favorite_projects` table for optimal query performance.

### Query Optimization

- Favorites are loaded once per page load and stored in a set for O(1) lookup
- The favorites filter uses an efficient JOIN query
- Lazy loading is used for relationships to avoid N+1 queries

### Scalability

The feature is designed to scale:
- Indexes ensure fast lookups even with thousands of projects
- Per-user favorites don't impact other users
- AJAX requests are lightweight (no page reloads)

## Security Considerations

- **Authentication Required**: All favorite endpoints require user login
- **User Isolation**: Users can only manage their own favorites
- **CSRF Protection**: All POST requests use CSRF tokens
- **Input Validation**: Project IDs are validated before database operations
- **Cascade Delete**: Favorites are automatically cleaned up when users/projects are deleted

## Browser Compatibility

The feature works in all modern browsers:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Required browser features:
- Fetch API for AJAX requests
- ES6 JavaScript (arrow functions, const/let)
- CSS3 for animations

## Future Enhancements

Potential improvements for future versions:

1. **Favorite Count Badge**: Show number of favorites in summary cards
2. **Recently Used**: Track and show recently accessed projects
3. **Favorite Ordering**: Allow users to reorder their favorites
4. **Quick Access Menu**: Add favorites to navigation menu
5. **Keyboard Shortcuts**: Add keyboard shortcut to favorite/unfavorite
6. **Bulk Favorite**: Select and favorite multiple projects at once
7. **Favorites Dashboard**: Dedicated dashboard showing favorite project metrics
8. **Export Favorites**: Export list of favorite projects
9. **Favorite Teams**: Share favorite project lists with team members
10. **Smart Favorites**: Auto-suggest favorites based on usage patterns

## Troubleshooting

### Star Icon Not Appearing

**Symptom**: Star icon column is missing in project list

**Solution**: 
- Clear browser cache and reload
- Verify template file is up to date
- Check browser console for JavaScript errors

### Favorite Not Saving

**Symptom**: Clicking star doesn't persist the favorite

**Solution**:
- Check browser console for network errors
- Verify CSRF token is present in page
- Check database migration was applied
- Review server logs for errors

### Migration Fails

**Symptom**: Migration script fails to create table

**Solution**:
- Check database user has CREATE TABLE permissions
- Verify Alembic is up to date
- Check for conflicting table names
- Review migration logs for specific errors

## Support

For issues or questions about this feature:

1. Check the [FAQ](../README.md#faq) section
2. Review the [test cases](../../tests/test_favorite_projects.py) for usage examples
3. Check [GitHub Issues](https://github.com/yourusername/TimeTracker/issues)
4. Contact the development team

## Changelog

### Version 1.0.0 (2025-10-23)

**Added:**
- Initial implementation of favorite projects feature
- Star icon for each project in project list
- Favorites filter in projects page
- User model methods for managing favorites
- Project model methods for checking favorite status
- API endpoints for favorite/unfavorite actions
- Comprehensive test coverage
- Documentation

**Database:**
- Added `user_favorite_projects` table
- Migration script: `023_add_user_favorite_projects.py`

**Security:**
- CSRF protection on all favorite endpoints
- User authentication required
- Per-user favorite isolation

