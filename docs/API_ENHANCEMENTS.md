# API Documentation Enhancements

This document describes the enhancements made to the API documentation and response handling.

## Response Format Standardization

All API endpoints now use consistent response formats:

### Success Response
```json
{
  "success": true,
  "message": "Optional success message",
  "data": { ... }
}
```

### Error Response
```json
{
  "success": false,
  "error": "error_code",
  "message": "Error message",
  "errors": {
    "field": ["Error message"]
  },
  "details": { ... }
}
```

## Response Helpers

The `app/utils/api_responses.py` module provides helper functions:

- `success_response()` - Create success responses
- `error_response()` - Create error responses
- `validation_error_response()` - Create validation error responses
- `not_found_response()` - Create 404 responses
- `unauthorized_response()` - Create 401 responses
- `forbidden_response()` - Create 403 responses
- `paginated_response()` - Create paginated list responses
- `created_response()` - Create 201 Created responses
- `no_content_response()` - Create 204 No Content responses

## Usage Example

```python
from app.utils.api_responses import success_response, error_response, paginated_response

@api_v1_bp.route('/projects', methods=['GET'])
def list_projects():
    projects = Project.query.all()
    return paginated_response(
        items=[p.to_dict() for p in projects],
        page=1,
        per_page=50,
        total=len(projects)
    )

@api_v1_bp.route('/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = Project.query.get(project_id)
    if not project:
        return not_found_response('Project', project_id)
    return success_response(data=project.to_dict())
```

## Error Handling

Enhanced error handling is provided in `app/utils/error_handlers.py`:

- Automatic error response formatting for API endpoints
- Marshmallow validation error handling
- Database integrity error handling
- SQLAlchemy error handling
- Generic exception handling

## OpenAPI/Swagger Documentation

The API documentation is available at `/api/docs` and includes:

- Complete endpoint documentation
- Request/response schemas
- Authentication information
- Error response examples
- Code examples

## Schema Validation

All API endpoints should use Marshmallow schemas for validation:

```python
from app.schemas import ProjectCreateSchema

@api_v1_bp.route('/projects', methods=['POST'])
def create_project():
    schema = ProjectCreateSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    # Create project...
    return created_response(project.to_dict())
```

