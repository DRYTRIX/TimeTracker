"""API Documentation with Swagger UI"""

from flask import Blueprint, jsonify, render_template_string
from flask_swagger_ui import get_swaggerui_blueprint

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
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "TimeTracker REST API",
            "version": "1.0.0",
            "description": """
# TimeTracker REST API

A comprehensive REST API for time tracking, project management, and reporting.

## Authentication

All API endpoints require authentication using an API token. You can obtain an API token from the admin dashboard.

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
- **admin:all** - Full administrative access

## Rate Limiting

API requests are rate-limited to prevent abuse. Current limits:
- 100 requests per minute per token
- 1000 requests per hour per token

## Pagination

List endpoints support pagination with the following query parameters:
- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 50, max: 100)

Responses include pagination metadata:
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

## Error Responses

The API uses standard HTTP status codes:

- **200 OK** - Request successful
- **201 Created** - Resource created successfully
- **400 Bad Request** - Invalid input
- **401 Unauthorized** - Authentication required or invalid token
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **500 Internal Server Error** - Server error

Error responses include a JSON body:
```json
{
  "error": "Error type",
  "message": "Detailed error message"
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
            {"url": "/api/v1", "description": "REST API v1"},
            {"url": "", "description": "App root (for /api/analytics, etc.)"},
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
                        "name": {"type": "string"},
                        "description": {"type": "string", "nullable": True},
                        "project_id": {"type": "integer"},
                        "status": {"type": "string", "enum": ["todo", "in_progress", "review", "done", "cancelled"]},
                        "priority": {"type": "integer"},
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
                "Error": {"type": "object", "properties": {"error": {"type": "string"}, "message": {"type": "string"}}},
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
                    "description": "Start a new timer for the authenticated user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["project_id"],
                                    "properties": {"project_id": {"type": "integer"}, "task_id": {"type": "integer"}},
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
                        {"name": "forecast_days", "in": "query", "schema": {"type": "integer", "default": 7, "maximum": 14}},
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
                    "parameters": [{"name": "invoice_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
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
        },
    }

    return jsonify(spec)
