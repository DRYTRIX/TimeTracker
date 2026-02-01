# TimeTracker REST API Documentation

## Overview

The TimeTracker REST API provides programmatic access to all time tracking, project management, and reporting features. This API is designed for developers who want to integrate TimeTracker with other tools or build custom applications.

## Base URL

```
https://your-domain.com/api/v1
```

## Authentication

All API endpoints require authentication using API tokens. API tokens are managed by administrators through the admin dashboard.

### Creating API Tokens

1. Log in as an administrator
2. Navigate to **Admin > Security & Access > Api-tokens** (`/admin/api-tokens`)
3. Click **Create Token**
4. Fill in the required information:
   - **Name**: A descriptive name for the token
   - **Description**: Optional description
   - **User**: The user this token will authenticate as
   - **Scopes**: Select the permissions this token should have
   - **Expires In**: Optional expiration period in days

5. Click **Create Token**
6. **Important**: Copy the generated token immediately - you won't be able to see it again!

### Using API Tokens

Include your API token in every request using one of these methods:

#### Method 1: Bearer Token (Recommended)

```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
     https://your-domain.com/api/v1/projects
```

#### Method 2: API Key Header

```bash
curl -H "X-API-Key: YOUR_API_TOKEN" \
     https://your-domain.com/api/v1/projects
```

### Token Format

API tokens follow the format: `tt_<32_random_characters>`

Example: `tt_abc123def456ghi789jkl012mno345pq`

## Scopes

API tokens use scopes to control access to resources. When creating a token, select the appropriate scopes:

| Scope | Description |
|-------|-------------|
| `read:projects` | View projects |
| `write:projects` | Create and update projects |
| `read:time_entries` | View time entries |
| `write:time_entries` | Create and update time entries |
| `read:tasks` | View tasks |
| `write:tasks` | Create and update tasks |
| `read:clients` | View clients |
| `write:clients` | Create and update clients |
| `read:reports` | View reports and analytics |
| `read:users` | View user information |
| `admin:all` | Full administrative access (use with caution) |

**Note**: For most integrations, you'll want both `read` and `write` scopes for the resources you're working with.

## Pagination

List endpoints support pagination to handle large datasets efficiently:

### Query Parameters

- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 50, max: 100)

### Response Format

```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 150,
    "pages": 3,
    "has_next": true,
    "has_prev": false,
    "next_page": 2,
    "prev_page": null
  }
}
```

## Date/Time Format

All timestamps use ISO 8601 format:

- **Date**: `YYYY-MM-DD` (e.g., `2024-01-15`)
- **DateTime**: `YYYY-MM-DDTHH:MM:SS` or `YYYY-MM-DDTHH:MM:SSZ` (e.g., `2024-01-15T14:30:00Z`)

## Error Handling

### HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Authentication required or invalid token
- `403 Forbidden` - Insufficient permissions (scope issue)
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

### Error Response Format

```json
{
  "error": "Invalid token",
  "message": "The provided API token is invalid or expired"
}
```

For scope errors:
```json
{
  "error": "Insufficient permissions",
  "message": "This endpoint requires the 'write:projects' scope",
  "required_scope": "write:projects",
  "available_scopes": ["read:projects", "read:time_entries"]
}
```

## API Endpoints

### System

#### Get API Information
```
GET /api/v1/info
```

Returns API version and available endpoints. No authentication required.

**Response:**
```json
{
  "api_version": "v1",
  "app_version": "1.0.0",
  "documentation_url": "/api/docs",
  "endpoints": {
    "projects": "/api/v1/projects",
    "time_entries": "/api/v1/time-entries",
    "tasks": "/api/v1/tasks",
    "clients": "/api/v1/clients"
  }
}
```

#### Health Check
```
GET /api/v1/health
```

Check if the API is operational. No authentication required.

### Search

#### Global Search
```
GET /api/v1/search
```

Perform a global search across projects, tasks, clients, and time entries.

**Required Scope:** `read:projects`

**Query Parameters:**
- `q` (required) - Search query (minimum 2 characters)
- `limit` (optional) - Maximum number of results per category (default: 10, max: 50)
- `types` (optional) - Comma-separated list of types to search: `project`, `task`, `client`, `entry`

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://your-domain.com/api/v1/search?q=website&limit=10"
```

**Search by specific types:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://your-domain.com/api/v1/search?q=website&types=project,task"
```

**Response:**
```json
{
  "results": [
    {
      "type": "project",
      "category": "project",
      "id": 1,
      "title": "Website Redesign",
      "description": "Complete website overhaul",
      "url": "/projects/1",
      "badge": "Project"
    },
    {
      "type": "task",
      "category": "task",
      "id": 5,
      "title": "Update homepage",
      "description": "Website Redesign",
      "url": "/tasks/5",
      "badge": "In Progress"
    }
  ],
  "query": "website",
  "count": 2
}
```

**Search Behavior:**
- **Projects**: Searches in name and description (active projects only)
- **Tasks**: Searches in name and description (tasks from active projects only)
- **Clients**: Searches in name, email, and company
- **Time Entries**: Searches in notes and tags (non-admin users see only their own entries)

**Error Responses:**
- `400 Bad Request` - Query is too short (less than 2 characters)
- `401 Unauthorized` - Missing or invalid API token
- `403 Forbidden` - Token lacks `read:projects` scope

**Note:** The legacy endpoint `/api/search` is also available for session-based authentication (requires login).

### Projects

#### List Projects
```
GET /api/v1/projects
```

**Required Scope:** `read:projects`

**Query Parameters:**
- `status` - Filter by status (`active`, `archived`, `on_hold`)
- `client_id` - Filter by client ID
- `page` - Page number
- `per_page` - Items per page

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://your-domain.com/api/v1/projects?status=active&per_page=20"
```

**Response:**
```json
{
  "projects": [
    {
      "id": 1,
      "name": "Website Redesign",
      "description": "Complete website overhaul",
      "client_id": 5,
      "hourly_rate": 75.00,
      "estimated_hours": 120,
      "status": "active",
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "pagination": {...}
}
```

#### Get Project
```
GET /api/v1/projects/{project_id}
```

**Required Scope:** `read:projects`

#### Create Project
```
POST /api/v1/projects
```

**Required Scope:** `write:projects`

**Request Body:**
```json
{
  "name": "New Project",
  "description": "Project description",
  "client_id": 5,
  "hourly_rate": 75.00,
  "estimated_hours": 100,
  "status": "active"
}
```

#### Update Project
```
PUT /api/v1/projects/{project_id}
```

**Required Scope:** `write:projects`

#### Archive Project
```
DELETE /api/v1/projects/{project_id}
```

**Required Scope:** `write:projects`

Note: This archives the project rather than permanently deleting it.

### Time Entries

#### List Time Entries
```
GET /api/v1/time-entries
```

**Required Scope:** `read:time_entries`

**Query Parameters:**
- `project_id` - Filter by project
- `user_id` - Filter by user (admin only)
- `start_date` - Filter by start date (ISO format)
- `end_date` - Filter by end date (ISO format)
- `billable` - Filter by billable status (`true` or `false`)
- `include_active` - Include active timers (`true` or `false`)
- `page` - Page number
- `per_page` - Items per page

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://your-domain.com/api/v1/time-entries?project_id=1&start_date=2024-01-01"
```

#### Create Time Entry
```
POST /api/v1/time-entries
```

**Required Scope:** `write:time_entries`

**Request Body:**
```json
{
  "project_id": 1,
  "task_id": 5,
  "start_time": "2024-01-15T09:00:00Z",
  "end_time": "2024-01-15T17:00:00Z",
  "notes": "Worked on feature X",
  "tags": "development,frontend",
  "billable": true
}
```

**Note:** `end_time` is optional. Omit it to create an active timer.

#### Update Time Entry
```
PUT /api/v1/time-entries/{entry_id}
```

**Required Scope:** `write:time_entries`

#### Delete Time Entry
```
DELETE /api/v1/time-entries/{entry_id}
```

**Required Scope:** `write:time_entries`

### Timer Control

#### Get Timer Status
```
GET /api/v1/timer/status
```

**Required Scope:** `read:time_entries`

Returns the current active timer for the authenticated user.

#### Start Timer
```
POST /api/v1/timer/start
```

**Required Scope:** `write:time_entries`

**Request Body:**
```json
{
  "project_id": 1,
  "task_id": 5
}
```

#### Stop Timer
```
POST /api/v1/timer/stop
```

**Required Scope:** `write:time_entries`

Stops the active timer for the authenticated user.

### Tasks

#### List Tasks
```
GET /api/v1/tasks
```

**Required Scope:** `read:tasks`

**Query Parameters:**
- `project_id` - Filter by project
- `status` - Filter by status
- `page` - Page number
- `per_page` - Items per page

#### Create Task
```
POST /api/v1/tasks
```

**Required Scope:** `write:tasks`

**Request Body:**
```json
{
  "name": "Implement login feature",
  "description": "Add user authentication",
  "project_id": 1,
  "status": "todo",
  "priority": 1
}
```

### Clients

#### List Clients
```
GET /api/v1/clients
```

**Required Scope:** `read:clients`

#### Create Client
```
POST /api/v1/clients
```

**Required Scope:** `write:clients`

**Request Body:**
```json
{
  "name": "Acme Corp",
  "email": "contact@acme.com",
  "company": "Acme Corporation",
  "phone": "+1-555-0123"
}
```

### Reports

#### Get Summary Report
```
GET /api/v1/reports/summary
```

**Required Scope:** `read:reports`

**Query Parameters:**
- `start_date` - Start date (ISO format)
- `end_date` - End date (ISO format)
- `project_id` - Filter by project
- `user_id` - Filter by user (admin only)

**Response:**
```json
{
  "summary": {
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-31T23:59:59Z",
    "total_hours": 160.5,
    "billable_hours": 145.0,
    "total_entries": 85,
    "by_project": [
      {
        "project_id": 1,
        "project_name": "Website Redesign",
        "hours": 85.5,
        "entries": 45
      }
    ]
  }
}
```

### Users

#### Get Current User
```
GET /api/v1/users/me
```

**Required Scope:** `read:users`

Returns information about the authenticated user.

## Interactive API Documentation

For interactive API documentation and testing, visit:

```
https://your-domain.com/api/docs
```

This Swagger UI interface allows you to:
- Browse all available endpoints
- Test API calls directly from your browser
- View detailed request/response schemas
- Try out different parameters

## Code Examples

### Python

```python
import requests

API_TOKEN = "tt_your_token_here"
BASE_URL = "https://your-domain.com/api/v1"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# List projects
response = requests.get(f"{BASE_URL}/projects", headers=headers)
projects = response.json()

# Create time entry
time_entry = {
    "project_id": 1,
    "start_time": "2024-01-15T09:00:00Z",
    "end_time": "2024-01-15T17:00:00Z",
    "notes": "Development work",
    "billable": True
}
response = requests.post(f"{BASE_URL}/time-entries", json=time_entry, headers=headers)
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const API_TOKEN = 'tt_your_token_here';
const BASE_URL = 'https://your-domain.com/api/v1';

const headers = {
  'Authorization': `Bearer ${API_TOKEN}`,
  'Content-Type': 'application/json'
};

// List projects
axios.get(`${BASE_URL}/projects`, { headers })
  .then(response => console.log(response.data))
  .catch(error => console.error(error));

// Start timer
axios.post(`${BASE_URL}/timer/start`, 
  { project_id: 1, task_id: 5 }, 
  { headers }
)
  .then(response => console.log('Timer started:', response.data))
  .catch(error => console.error(error));
```

### cURL

```bash
# List projects
curl -H "Authorization: Bearer tt_your_token_here" \
     https://your-domain.com/api/v1/projects

# Create time entry
curl -X POST \
     -H "Authorization: Bearer tt_your_token_here" \
     -H "Content-Type: application/json" \
     -d '{"project_id":1,"start_time":"2024-01-15T09:00:00Z","end_time":"2024-01-15T17:00:00Z"}' \
     https://your-domain.com/api/v1/time-entries
```

## Best Practices

### Security

1. **Store tokens securely**: Never commit tokens to version control
2. **Use environment variables**: Store tokens in environment variables
3. **Rotate tokens regularly**: Create new tokens periodically and delete old ones
4. **Use minimal scopes**: Only grant the permissions needed
5. **Set expiration dates**: Configure tokens to expire when appropriate

### Performance

1. **Use pagination**: Don't fetch all records at once
2. **Filter results**: Use query parameters to reduce data transfer
3. **Cache responses**: Cache data that doesn't change frequently
4. **Batch operations**: Combine multiple operations when possible

### Error Handling

1. **Check status codes**: Always check HTTP status codes
2. **Handle rate limits**: Implement exponential backoff for rate limit errors
3. **Log errors**: Log API errors for debugging
4. **Validate input**: Validate data before sending to API

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Per-token limits**: 100 requests per minute, 1000 requests per hour
- **Response headers**: Rate limit information is included in response headers
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Unix timestamp when the limit resets

When rate limited, you'll receive a `429 Too Many Requests` response.

## Webhook Support (Coming Soon)

Webhook support for real-time notifications is planned for a future release. This will allow you to receive notifications when:
- Time entries are created/updated
- Projects change status
- Tasks are completed
- Timer events occur

## Support

For API support:
- **Documentation**: This guide and `/api/docs`
- **GitHub Issues**: Report bugs and request features
- **Community**: Join our community forum

## Changelog

### Version 1.0.0 (Current)
- Initial REST API release
- Full CRUD operations for projects, time entries, tasks, and clients
- Token-based authentication with scopes
- Comprehensive filtering and pagination
- Timer control endpoints
- Reporting endpoints
- Interactive Swagger documentation

