"""
API v1 - Projects sub-blueprint.
Routes under /api/v1/projects.
"""

from flask import Blueprint, jsonify, request, g
from marshmallow import ValidationError
from app.utils.api_auth import require_api_token
from app.utils.api_responses import (
    error_response,
    forbidden_response,
    handle_validation_error,
    not_found_response,
    validation_error_response,
)

api_v1_projects_bp = Blueprint("api_v1_projects", __name__, url_prefix="/api/v1")


@api_v1_projects_bp.route("/projects", methods=["GET"])
@require_api_token("read:projects")
def list_projects():
    """List all projects."""
    from app.services import ProjectService
    from app.utils.scope_filter import get_allowed_client_ids

    status = request.args.get("status", "active")
    client_id = request.args.get("client_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)
    scope_client_ids = get_allowed_client_ids(g.api_user)

    project_service = ProjectService()
    result = project_service.list_projects(
        status=status,
        client_id=client_id,
        page=page,
        per_page=per_page,
        scope_client_ids=scope_client_ids,
    )
    pag = result["pagination"]
    pagination_dict = {
        "page": pag.page,
        "per_page": pag.per_page,
        "total": pag.total,
        "pages": pag.pages,
        "has_next": pag.has_next,
        "has_prev": pag.has_prev,
        "next_page": pag.page + 1 if pag.has_next else None,
        "prev_page": pag.page - 1 if pag.has_prev else None,
    }
    return jsonify({"projects": [p.to_dict() for p in result["projects"]], "pagination": pagination_dict})


@api_v1_projects_bp.route("/projects/<int:project_id>", methods=["GET"])
@require_api_token("read:projects")
def get_project(project_id):
    """Get a specific project."""
    from app.services import ProjectService
    from app.utils.scope_filter import user_can_access_project

    project_service = ProjectService()
    result = project_service.get_project_with_details(project_id=project_id, include_time_entries=False)

    if not result:
        return not_found_response("Project", project_id)
    if not user_can_access_project(g.api_user, project_id):
        return forbidden_response("You do not have access to this project")

    return jsonify({"project": result.to_dict()})


@api_v1_projects_bp.route("/projects", methods=["POST"])
@require_api_token("write:projects")
def create_project():
    """Create a new project."""
    from app.schemas import ProjectCreateSchema
    from app.services import ProjectService

    data = request.get_json() or {}
    if not data.get("name"):
        return validation_error_response(
            errors={"name": ["Project name is required"]},
            message="Project name is required",
        )
    try:
        loaded = ProjectCreateSchema(partial=True).load(data)
    except ValidationError as err:
        return handle_validation_error(err)

    project_service = ProjectService()
    result = project_service.create_project(
        name=loaded["name"],
        client_id=loaded.get("client_id"),
        created_by=g.api_user.id,
        description=loaded.get("description"),
        billable=loaded.get("billable", True),
        hourly_rate=loaded.get("hourly_rate"),
        code=loaded.get("code"),
        budget_amount=loaded.get("budget_amount"),
        budget_threshold_percent=loaded.get("budget_threshold_percent"),
        billing_ref=loaded.get("billing_ref"),
    )

    if not result.get("success"):
        return error_response(result.get("message", "Could not create project"), status_code=400)

    return jsonify({"message": "Project created successfully", "project": result["project"].to_dict()}), 201


@api_v1_projects_bp.route("/projects/<int:project_id>", methods=["PUT", "PATCH"])
@require_api_token("write:projects")
def update_project(project_id):
    """Update a project."""
    from app.services import ProjectService

    data = request.get_json() or {}
    project_service = ProjectService()
    update_kwargs = {}
    if "name" in data:
        update_kwargs["name"] = data["name"]
    if "description" in data:
        update_kwargs["description"] = data["description"]
    if "client_id" in data:
        update_kwargs["client_id"] = data["client_id"]
    if "hourly_rate" in data:
        update_kwargs["hourly_rate"] = data["hourly_rate"]
    if "estimated_hours" in data:
        update_kwargs["estimated_hours"] = data["estimated_hours"]
    if "status" in data:
        update_kwargs["status"] = data["status"]
    if "code" in data:
        update_kwargs["code"] = data["code"]
    if "budget_amount" in data:
        update_kwargs["budget_amount"] = data["budget_amount"]
    if "billing_ref" in data:
        update_kwargs["billing_ref"] = data["billing_ref"]

    result = project_service.update_project(project_id=project_id, user_id=g.api_user.id, **update_kwargs)

    if not result.get("success"):
        return error_response(result.get("message", "Could not update project"), status_code=400)

    return jsonify({"message": "Project updated successfully", "project": result["project"].to_dict()})


@api_v1_projects_bp.route("/projects/<int:project_id>", methods=["DELETE"])
@require_api_token("write:projects")
def delete_project(project_id):
    """Delete/archive a project."""
    from app.services import ProjectService

    project_service = ProjectService()
    result = project_service.archive_project(
        project_id=project_id, user_id=g.api_user.id, reason="Archived via API"
    )

    if not result.get("success"):
        return error_response(result.get("message", "Could not archive project"), status_code=404)

    return jsonify({"message": "Project archived successfully"})
