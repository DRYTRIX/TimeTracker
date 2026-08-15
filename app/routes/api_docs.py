"""API Documentation with Swagger UI"""

from flask import Blueprint, current_app, jsonify, render_template_string
from flask_swagger_ui import get_swaggerui_blueprint

from app.config.analytics_defaults import get_version_from_setup

# Create blueprint for serving OpenAPI spec
api_docs_bp = Blueprint("api_docs", __name__)

SWAGGER_URL = "/api/docs"
API_URL = "/api/openapi.json"

# Create Swagger UI blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        "app_name": "TimeTracker REST API",
        "defaultModelsExpandDepth": -1,
        "displayRequestDuration": True,
        "docExpansion": "list",
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "syntaxHighlight.theme": "monokai",
    },
)


@api_docs_bp.route("/api/openapi.json")
def openapi_spec():
    """Serve the OpenAPI specification"""
    app_version = get_version_from_setup()
    if app_version == "unknown":
        app_version = current_app.config.get("APP_VERSION", "1.0.0")

    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "TimeTracker REST API",
            "version": app_version,
            "description": """
# TimeTracker REST API

A comprehensive REST API for time tracking, project management, and reporting.

## Two HTTP JSON surfaces

TimeTracker exposes two JSON HTTP surfaces. **This OpenAPI document describes only `/api/v1`** (paths are relative to the v1 server URL).

1. **`/api/v1` (documented here)** — Primary, versioned **REST API** for integrations (desktop, mobile, automation). Uses **API token** authentication (`Authorization: Bearer` or `X-API-Key`), scoped permissions, and stable JSON contracts.

2. **`/api/*` (not fully documented here)** — Same-origin **session** JSON used by the **logged-in web UI** (Flask-Login cookie): search, timer helpers, notifications, dashboard fragments, uploads, and similar. These routes may change with the UI. Where a v1 equivalent exists, legacy `/api` routes may return **`X-API-Deprecated: true`** and a **`Link`** header with `rel="successor-version"` pointing at the v1 path. **Integrations should not rely on `/api/*`.**

**Exception:** a few `/api` routes (for example version check/dismiss) may accept **either** session or token for admin tooling; see product docs for details.

## Authentication (paths under `/api/v1` in this spec)

All **documented** API endpoints use authentication as described below. You can obtain an API token from the admin dashboard.

### Authentication Methods

The API supports two authentication methods:

1. **Bearer Token** (Recommended):
   ```
   Authorization: Bearer YOUR_API_TOKEN
   ```

2. **API Key Header**:
   ```
   X-API-Key: YOUR_API_TOKEN
   ```

### Token Format

API tokens follow the format: `tt_<32_random_characters>`

Example:
```
tt_abc123def456ghi789jkl012mno345
```

## Scopes

API tokens are assigned specific scopes that define what resources they can access:

- **read:projects** - View projects
- **write:projects** - Create and update projects
- **read:time_entries** - View time entries
- **write:time_entries** - Create and update time entries
- **read:tasks** - View tasks
- **write:tasks** - Create and update tasks
- **read:clients** - View clients
- **write:clients** - Create and update clients
- **read:reports** - View reports and analytics
- **read:users** - View user information
- **read:ai** - Preview AI helper context
- **write:ai** - Chat with the AI helper and confirm proposed actions
- **admin:all** - Full administrative access

## Rate Limiting

API requests are rate-limited to prevent abuse. Current limits:
- 100 requests per minute per token
- 1000 requests per hour per token

## Pagination

List endpoints support pagination with the following query parameters:
- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 50, max: 100)

List responses use a **resource-named key** plus `pagination` (e.g. `time_entries`, `projects`, `clients`). Example:
```json
{
  "time_entries": [...],
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

## Error Responses

The API uses standard HTTP status codes:

- **200 OK** - Request successful
- **201 Created** - Resource created successfully
- **400 Bad Request** - Invalid input
- **401 Unauthorized** - Authentication required or invalid token
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **500 Internal Server Error** - Server error

Error responses include a JSON body with at least `error` (user-facing message) and `message`; optional `error_code` (e.g. unauthorized, forbidden, not_found, validation_error) and `errors` (field-level validation):
```json
{
  "error": "Invalid token",
  "message": "The provided API token is invalid or expired",
  "error_code": "unauthorized"
}
```
Validation errors (400):
```json
{
  "error": "Validation failed",
  "message": "Validation failed",
  "error_code": "validation_error",
  "errors": { "field_name": ["message1", "message2"] }
}
```

## Date/Time Format

All timestamps use ISO 8601 format:
- **Date**: `YYYY-MM-DD`
- **DateTime**: `YYYY-MM-DDTHH:MM:SS` or `YYYY-MM-DDTHH:MM:SSZ`

Example: `2024-01-15T14:30:00Z`
            """,
            "contact": {"name": "TimeTracker API Support"},
            "license": {"name": "MIT"},
        },
        "servers": [
            {
                "url": "/api/v1",
                "description": "Versioned REST API (token auth); OpenAPI paths are relative to this base.",
            },
            {
                "url": "",
                "description": "Application origin only (HTML, static assets, session `/api/*`, and other non-spec routes—not covered by this document).",
            },
        ],
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "API Token",
                    "description": "Enter your API token (format: tt_xxxxx...)",
                },
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "API token in X-API-Key header",
                },
            },
            "schemas": {
                "Project": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "client_id": {"type": "integer", "nullable": True},
                        "hourly_rate": {"type": "number"},
                        "estimated_hours": {"type": "number", "nullable": True},
                        "status": {"type": "string", "enum": ["active", "archived", "on_hold"]},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                },
                "TimeEntry": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "user_id": {"type": "integer"},
                        "project_id": {"type": "integer"},
                        "task_id": {"type": "integer", "nullable": True},
                        "start_time": {"type": "string", "format": "date-time"},
                        "end_time": {"type": "string", "format": "date-time", "nullable": True},
                        "duration_hours": {"type": "number", "nullable": True},
                        "notes": {"type": "string", "nullable": True},
                        "tags": {"type": "string", "nullable": True},
                        "billable": {"type": "boolean"},
                        "source": {"type": "string"},
                    },
                },
                "Task": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "project_id": {"type": "integer"},
                        "name": {"type": "string"},
                        "description": {"type": "string", "nullable": True},
                        "status": {"type": "string", "enum": ["todo", "in_progress", "review", "done", "cancelled"]},
                        "status_display": {"type": "string", "description": "Human-readable status label"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                        "priority_display": {"type": "string", "description": "Human-readable priority label"},
                        "priority_class": {"type": "string", "description": "CSS class for priority styling"},
                        "estimated_hours": {"type": "number", "nullable": True},
                        "due_date": {"type": "string", "format": "date", "nullable": True},
                        "assigned_to": {"type": "integer", "nullable": True, "description": "User ID of the assignee"},
                        "assigned_user": {"type": "string", "nullable": True, "description": "Username of the assignee"},
                        "created_by": {"type": "integer", "description": "User ID of the creator"},
                        "creator": {"type": "string", "nullable": True, "description": "Username of the creator"},
                        "created_at": {"type": "string", "format": "date-time", "nullable": True},
                        "updated_at": {"type": "string", "format": "date-time", "nullable": True},
                        "started_at": {"type": "string", "format": "date-time", "nullable": True},
                        "completed_at": {"type": "string", "format": "date-time", "nullable": True},
                        "total_hours": {"type": "number", "description": "Total hours tracked on this task"},
                        "total_billable_hours": {"type": "number", "description": "Total billable hours"},
                        "progress_percentage": {"type": "number", "description": "Progress based on estimated vs actual hours"},
                        "is_active": {"type": "boolean", "description": "True if task is not done or cancelled"},
                        "is_overdue": {"type": "boolean", "description": "True if past due date and not closed"},
                        "tags": {"type": "string", "nullable": True, "description": "Comma-separated tag string"},
                        "tag_list": {"type": "array", "items": {"type": "string"}, "description": "Tags as a list"},
                    },
                },
                "Client": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string", "nullable": True},
                        "company": {"type": "string", "nullable": True},
                        "phone": {"type": "string", "nullable": True},
                    },
                },
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string", "description": "User-facing error message"},
                        "message": {"type": "string", "description": "Detailed error message"},
                        "error_code": {
                            "type": "string",
                            "description": "Machine-readable code (e.g. unauthorized, forbidden, not_found, validation_error)",
                        },
                        "errors": {
                            "type": "object",
                            "additionalProperties": {"type": "array", "items": {"type": "string"}},
                            "description": "Field-level validation errors",
                        },
                        "required_scope": {"type": "string"},
                        "available_scopes": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "Pagination": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer"},
                        "per_page": {"type": "integer"},
                        "total": {"type": "integer"},
                        "pages": {"type": "integer"},
                        "has_next": {"type": "boolean"},
                        "has_prev": {"type": "boolean"},
                        "next_page": {"type": "integer", "nullable": True},
                        "prev_page": {"type": "integer", "nullable": True},
                    },
                },
            },
        },
        "security": [{"BearerAuth": []}, {"ApiKeyAuth": []}],
        "tags": [
            {
                "name": "SessionWebApi",
                "description": "Session-based JSON under `/api/*` is for the browser UI only; it is not defined in this spec. Use `/api/v1` for integrations.",
            },
            {"name": "System", "description": "System information and health checks"},
            {"name": "Projects", "description": "Project management operations"},
            {"name": "Time Entries", "description": "Time tracking operations"},
            {"name": "Timer", "description": "Timer control operations"},
            {"name": "Tasks", "description": "Task management operations"},
            {"name": "Clients", "description": "Client management operations"},
            {"name": "Reports", "description": "Reporting and analytics"},
            {"name": "Users", "description": "User management operations"},
            {"name": "Invoices", "description": "Invoice operations"},
            {"name": "Expenses", "description": "Expense operations"},
            {
                "name": "AI Helper",
                "description": "Server-side AI helper for chat, context preview, and confirmed actions",
            },
        ],
        "paths": {
            "/info": {
                "get": {
                    "tags": ["System"],
                    "summary": "Get API information",
                    "description": "Returns API version and available endpoints",
                    "security": [],
                    "responses": {
                        "200": {
                            "description": "API information",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "api_version": {"type": "string"},
                                            "app_version": {"type": "string"},
                                            "documentation_url": {"type": "string"},
                                            "endpoints": {"type": "object"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/health": {
                "get": {
                    "tags": ["System"],
                    "summary": "Health check",
                    "description": "Check if the API is healthy and operational",
                    "security": [],
                    "responses": {"200": {"description": "API is healthy"}},
                }
            },
            "/ai/context-preview": {
                "get": {
                    "tags": ["AI Helper"],
                    "summary": "Preview AI context",
                    "description": "Return the compact TimeTracker context that would be sent to the AI helper.",
                    "responses": {"200": {"description": "Context preview"}, "401": {"description": "Unauthorized"}},
                }
            },
            "/ai/chat": {
                "post": {
                    "tags": ["AI Helper"],
                    "summary": "Chat with AI helper",
                    "description": "Send a prompt to the server-side AI helper. Requires the write:ai scope.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["prompt"],
                                    "properties": {
                                        "prompt": {"type": "string"},
                                        "history": {"type": "array", "items": {"type": "object"}},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "AI response"},
                        "400": {"description": "AI disabled or invalid input"},
                    },
                }
            },
            "/ai/actions/confirm": {
                "post": {
                    "tags": ["AI Helper"],
                    "summary": "Confirm AI action",
                    "description": "Execute a user-confirmed action proposed by the AI helper.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["action"],
                                    "properties": {"action": {"type": "object"}},
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Action completed"},
                        "400": {"description": "Unsupported action"},
                    },
                }
            },
            "/projects": {
                "get": {
                    "tags": ["Projects"],
                    "summary": "List projects",
                    "description": "Get a paginated list of projects",
                    "parameters": [
                        {
                            "name": "status",
                            "in": "query",
                            "schema": {"type": "string", "enum": ["active", "archived", "on_hold"]},
                        },
                        {"name": "client_id", "in": "query", "schema": {"type": "integer"}},
                        {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                        {
                            "name": "per_page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 50, "maximum": 100},
                        },
                    ],
                    "responses": {"200": {"description": "List of projects"}, "401": {"description": "Unauthorized"}},
                },
                "post": {
                    "tags": ["Projects"],
                    "summary": "Create project",
                    "description": "Create a new project",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "client_id": {"type": "integer"},
                                        "hourly_rate": {"type": "number"},
                                        "estimated_hours": {"type": "number"},
                                        "status": {
                                            "type": "string",
                                            "enum": ["active", "archived", "on_hold"],
                                            "default": "active",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"201": {"description": "Project created"}, "400": {"description": "Invalid input"}},
                },
            },
            "/projects/{project_id}": {
                "get": {
                    "tags": ["Projects"],
                    "summary": "Get project",
                    "description": "Get details of a specific project",
                    "parameters": [
                        {"name": "project_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {"description": "Project details"},
                        "404": {"description": "Project not found"},
                    },
                },
                "put": {
                    "tags": ["Projects"],
                    "summary": "Update project",
                    "description": "Update an existing project",
                    "parameters": [
                        {"name": "project_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Project"}}},
                    },
                    "responses": {
                        "200": {"description": "Project updated"},
                        "404": {"description": "Project not found"},
                    },
                },
                "delete": {
                    "tags": ["Projects"],
                    "summary": "Archive project",
                    "description": "Archive a project (soft delete)",
                    "parameters": [
                        {"name": "project_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {"description": "Project archived"},
                        "404": {"description": "Project not found"},
                    },
                },
            },
            "/time-entries": {
                "get": {
                    "tags": ["Time Entries"],
                    "summary": "List time entries",
                    "description": "Get a paginated list of time entries",
                    "parameters": [
                        {"name": "project_id", "in": "query", "schema": {"type": "integer"}},
                        {"name": "user_id", "in": "query", "schema": {"type": "integer"}},
                        {"name": "start_date", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "end_date", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "billable", "in": "query", "schema": {"type": "boolean"}},
                        {"name": "page", "in": "query", "schema": {"type": "integer"}},
                        {"name": "per_page", "in": "query", "schema": {"type": "integer"}},
                    ],
                    "responses": {"200": {"description": "List of time entries"}},
                },
                "post": {
                    "tags": ["Time Entries"],
                    "summary": "Create time entry",
                    "description": "Create a new time entry",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["project_id", "start_time"],
                                    "properties": {
                                        "project_id": {"type": "integer"},
                                        "task_id": {"type": "integer"},
                                        "start_time": {"type": "string", "format": "date-time"},
                                        "end_time": {"type": "string", "format": "date-time"},
                                        "notes": {"type": "string"},
                                        "tags": {"type": "string"},
                                        "billable": {"type": "boolean", "default": True},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"201": {"description": "Time entry created"}},
                },
            },
            "/timer/status": {
                "get": {
                    "tags": ["Timer"],
                    "summary": "Get timer status",
                    "description": "Get the current timer status for the authenticated user",
                    "responses": {"200": {"description": "Timer status"}},
                }
            },
            "/timer/start": {
                "post": {
                    "tags": ["Timer"],
                    "summary": "Start timer",
                    "description": (
                        "Start a new timer for the authenticated user. "
                        "Provide project_id and/or client_id (at least one required). "
                        "Client-only timers omit project_id; task_id requires project_id."
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "project_id": {"type": "integer"},
                                        "client_id": {"type": "integer"},
                                        "task_id": {"type": "integer"},
                                        "notes": {"type": "string"},
                                        "template_id": {"type": "integer"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"201": {"description": "Timer started"}},
                }
            },
            "/timer/stop": {
                "post": {
                    "tags": ["Timer"],
                    "summary": "Stop timer",
                    "description": "Stop the active timer for the authenticated user",
                    "responses": {"200": {"description": "Timer stopped"}},
                }
            },
            "/users/me": {
                "get": {
                    "tags": ["Users"],
                    "summary": "Get current user",
                    "description": "Get information about the authenticated user",
                    "responses": {"200": {"description": "User information"}},
                }
            },
            "/analytics/hours-by-day": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Hours by day",
                    "description": "Get hours worked per day for a date range",
                    "parameters": [{"name": "days", "in": "query", "schema": {"type": "integer", "default": 30}}],
                    "responses": {"200": {"description": "Chart data with labels and datasets"}},
                }
            },
            "/analytics/hours-forecast": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Hours forecast",
                    "description": "Get forecasted hours for the next 7 days based on moving average",
                    "parameters": [
                        {"name": "days", "in": "query", "schema": {"type": "integer", "default": 30}},
                        {
                            "name": "forecast_days",
                            "in": "query",
                            "schema": {"type": "integer", "default": 7, "maximum": 14},
                        },
                    ],
                    "responses": {"200": {"description": "Historical and forecast data"}},
                }
            },
            "/analytics/summary-with-comparison": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Summary with comparison",
                    "description": "Get summary metrics with comparison to previous period",
                    "parameters": [{"name": "days", "in": "query", "schema": {"type": "integer", "default": 30}}],
                    "responses": {"200": {"description": "Summary with total hours, billable, entries, changes"}},
                }
            },
            "/invoices/{invoice_id}": {
                "get": {
                    "tags": ["Invoices"],
                    "summary": "Get invoice",
                    "parameters": [
                        {"name": "invoice_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "Invoice details"}, "404": {"description": "Not found"}},
                }
            },
            "/expenses": {
                "get": {
                    "tags": ["Expenses"],
                    "summary": "List expenses",
                    "parameters": [
                        {"name": "project_id", "in": "query", "schema": {"type": "integer"}},
                        {"name": "page", "in": "query", "schema": {"type": "integer"}},
                        {"name": "per_page", "in": "query", "schema": {"type": "integer"}},
                    ],
                    "responses": {"200": {"description": "List of expenses"}},
                }
            },
            "/tasks": {
                "get": {
                    "tags": ["Tasks"],
                    "summary": "List tasks",
                    "description": "Get a paginated list of tasks with optional filters",
                    "parameters": [
                        {"name": "project_id", "in": "query", "schema": {"type": "integer"}},
                        {"name": "status", "in": "query", "schema": {"type": "string"}},
                        {"name": "tags", "in": "query", "schema": {"type": "string"}},
                        {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                        {"name": "per_page", "in": "query", "schema": {"type": "integer", "default": 50, "maximum": 100}},
                    ],
                    "responses": {"200": {"description": "List of tasks"}, "401": {"description": "Unauthorized"}},
                },
                "post": {
                    "tags": ["Tasks"],
                    "summary": "Create task",
                    "description": "Create a new task",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name", "project_id"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "project_id": {"type": "integer"},
                                        "description": {"type": "string"},
                                        "assignee_id": {"type": "integer"},
                                        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "default": "medium"},
                                        "due_date": {"type": "string", "format": "date"},
                                        "estimated_hours": {"type": "number"},
                                        "tags": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Task created"},
                        "400": {"description": "Validation error"},
                    },
                },
            },
            "/tasks/{task_id}": {
                "get": {
                    "tags": ["Tasks"],
                    "summary": "Get task",
                    "description": "Get details of a specific task",
                    "parameters": [
                        {"name": "task_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {"description": "Task details"},
                        "404": {"description": "Task not found"},
                    },
                },
                "put": {
                    "tags": ["Tasks"],
                    "summary": "Update task",
                    "description": "Update an existing task (full or partial update)",
                    "parameters": [
                        {"name": "task_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "status": {"type": "string", "enum": ["todo", "in_progress", "review", "done", "cancelled"]},
                                        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                                        "assignee_id": {"type": "integer"},
                                        "due_date": {"type": "string", "format": "date"},
                                        "estimated_hours": {"type": "number"},
                                        "tags": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Task updated"},
                        "400": {"description": "Validation error"},
                        "404": {"description": "Task not found"},
                    },
                },
                "delete": {
                    "tags": ["Tasks"],
                    "summary": "Delete task",
                    "description": "Permanently delete a task",
                    "parameters": [
                        {"name": "task_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {"description": "Task deleted"},
                        "404": {"description": "Task not found"},
                    },
                },
            },
            "/clients": {
                "get": {
                    "tags": ["Clients"],
                    "summary": "List clients",
                    "description": "Get a paginated list of clients",
                    "parameters": [
                        {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                        {"name": "per_page", "in": "query", "schema": {"type": "integer", "default": 50, "maximum": 100}},
                    ],
                    "responses": {"200": {"description": "List of clients"}, "401": {"description": "Unauthorized"}},
                },
                "post": {
                    "tags": ["Clients"],
                    "summary": "Create client",
                    "description": "Create a new client",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string"},
                                        "company": {"type": "string"},
                                        "phone": {"type": "string"},
                                        "address": {"type": "string"},
                                        "default_hourly_rate": {"type": "number"},
                                        "custom_fields": {"type": "object"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Client created"},
                        "400": {"description": "Validation error"},
                    },
                },
            },
            "/clients/{client_id}": {
                "get": {
                    "tags": ["Clients"],
                    "summary": "Get client",
                    "description": "Get details of a specific client including associated projects",
                    "parameters": [
                        {"name": "client_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {"description": "Client details"},
                        "403": {"description": "Forbidden"},
                        "404": {"description": "Client not found"},
                    },
                },
            },
            "/clients/{client_id}/contacts": {
                "get": {
                    "tags": ["Clients"],
                    "summary": "List client contacts",
                    "description": "Get all active contacts for a client",
                    "parameters": [
                        {"name": "client_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "List of contacts"}, "404": {"description": "Client not found"}},
                },
                "post": {
                    "tags": ["Clients"],
                    "summary": "Create contact",
                    "description": "Create a new contact for a client",
                    "parameters": [
                        {"name": "client_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["first_name", "last_name"],
                                    "properties": {
                                        "first_name": {"type": "string"},
                                        "last_name": {"type": "string"},
                                        "email": {"type": "string"},
                                        "phone": {"type": "string"},
                                        "mobile": {"type": "string"},
                                        "title": {"type": "string"},
                                        "department": {"type": "string"},
                                        "role": {"type": "string", "default": "contact"},
                                        "is_primary": {"type": "boolean", "default": False},
                                        "address": {"type": "string"},
                                        "notes": {"type": "string"},
                                        "tags": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Contact created"},
                        "400": {"description": "Validation error"},
                        "404": {"description": "Client not found"},
                    },
                },
            },
            "/contacts/{contact_id}": {
                "get": {
                    "tags": ["Clients"],
                    "summary": "Get contact",
                    "description": "Get details of a specific contact",
                    "parameters": [
                        {"name": "contact_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "Contact details"}, "404": {"description": "Contact not found"}},
                },
                "put": {
                    "tags": ["Clients"],
                    "summary": "Update contact",
                    "description": "Update an existing contact",
                    "parameters": [
                        {"name": "contact_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Contact"}}}},
                    "responses": {"200": {"description": "Contact updated"}, "404": {"description": "Contact not found"}},
                },
                "delete": {
                    "tags": ["Clients"],
                    "summary": "Delete contact",
                    "description": "Soft-delete a contact (sets is_active=False)",
                    "parameters": [
                        {"name": "contact_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "Contact deleted"}, "404": {"description": "Contact not found"}},
                },
            },
            "/clients/{client_id}/notes": {
                "get": {
                    "tags": ["Clients"],
                    "summary": "List client notes",
                    "description": "Get paginated notes for a client (important notes first)",
                    "parameters": [
                        {"name": "client_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                        {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                        {"name": "per_page", "in": "query", "schema": {"type": "integer", "default": 50, "maximum": 100}},
                    ],
                    "responses": {"200": {"description": "List of notes"}, "404": {"description": "Client not found"}},
                },
                "post": {
                    "tags": ["Clients"],
                    "summary": "Create client note",
                    "description": "Create a new note for a client",
                    "parameters": [{"name": "client_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "required": ["content"], "properties": {"content": {"type": "string"}, "is_important": {"type": "boolean", "default": False}}}}},
                    },
                    "responses": {"201": {"description": "Note created"}, "400": {"description": "content is required"}, "404": {"description": "Client not found"}},
                },
            },
            "/client-notes/{note_id}": {
                "get": {
                    "tags": ["Clients"],
                    "summary": "Get client note",
                    "parameters": [{"name": "note_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Note details"}, "404": {"description": "Note not found"}},
                },
                "put": {
                    "tags": ["Clients"],
                    "summary": "Update client note",
                    "description": "Update an existing client note (author or admin only)",
                    "parameters": [{"name": "note_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "required": ["content"], "properties": {"content": {"type": "string"}, "is_important": {"type": "boolean"}}}}}},
                    "responses": {"200": {"description": "Note updated"}, "400": {"description": "content is required"}, "403": {"description": "Access denied"}, "404": {"description": "Note not found"}},
                },
                "delete": {
                    "tags": ["Clients"],
                    "summary": "Delete client note",
                    "description": "Delete a client note (author or admin only)",
                    "parameters": [{"name": "note_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Note deleted"}, "403": {"description": "Access denied"}, "404": {"description": "Note not found"}},
                },
            },
            "/clients/{client_id}/invoice-unbilled": {
                "post": {
                    "tags": ["Clients"],
                    "summary": "Create invoice from unbilled time",
                    "description": "Create a draft invoice from all unbilled billable time entries for this client (grouped by project)",
                    "parameters": [{"name": "client_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Invoice created (returns invoice_id, invoice_number, total, item_count)"}, "400": {"description": "Cannot create invoice"}, "404": {"description": "Client not found"}},
                },
            },
        },
    }

    return jsonify(spec)
