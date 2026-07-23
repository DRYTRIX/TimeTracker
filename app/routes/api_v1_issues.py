"""
API v1 - Issues sub-blueprint.
Routes under /api/v1/issues.
"""

from flask import Blueprint, g, jsonify, request

from app import db
from app.models import Issue
from app.routes.api_v1_common import _require_module_enabled_for_api
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, forbidden_response, not_found_response

api_v1_issues_bp = Blueprint("api_v1_issues", __name__, url_prefix="/api/v1")


@api_v1_issues_bp.route("/issues", methods=["GET"])
@require_api_token("read:projects")
def list_issues():
    """List issues with optional filters."""
    blocked = _require_module_enabled_for_api("issues")
    if blocked:
        return blocked

    project_id = request.args.get("project_id", type=int)
    client_id = request.args.get("client_id", type=int)
    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)

    query = Issue.query
    if project_id:
        query = query.filter_by(project_id=project_id)
    if client_id:
        query = query.filter_by(client_id=client_id)
    if status:
        query = query.filter_by(status=status)

    query = query.order_by(Issue.updated_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    return jsonify({"issues": [i.to_dict() for i in pagination.items], "pagination": pagination_dict})


@api_v1_issues_bp.route("/issues/<int:issue_id>", methods=["GET"])
@require_api_token("read:projects")
def get_issue(issue_id):
    """Get a single issue."""
    blocked = _require_module_enabled_for_api("issues")
    if blocked:
        return blocked
    issue = Issue.query.filter_by(id=issue_id).first()
    if not issue:
        return not_found_response("Issue not found")
    return jsonify({"issue": issue.to_dict()})


@api_v1_issues_bp.route("/issues", methods=["POST"])
@require_api_token("write:projects")
def create_issue():
    """Create an issue."""
    blocked = _require_module_enabled_for_api("issues")
    if blocked:
        return blocked

    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    client_id = data.get("client_id")
    if not title:
        return error_response("title is required", status_code=400)
    if not client_id:
        return error_response("client_id is required", status_code=400)

    issue = Issue(
        client_id=int(client_id),
        title=title,
        description=data.get("description"),
        project_id=data.get("project_id"),
        task_id=data.get("task_id"),
        priority=(data.get("priority") or "medium").strip(),
        status=(data.get("status") or "open").strip(),
        submitted_by_client=bool(data.get("submitted_by_client", False)),
        assigned_to=data.get("assigned_to"),
        created_by=g.api_user.id,
    )
    db.session.add(issue)
    db.session.commit()
    return jsonify({"message": "Issue created successfully", "issue": issue.to_dict()}), 201


@api_v1_issues_bp.route("/issues/<int:issue_id>", methods=["PUT", "PATCH"])
@require_api_token("write:projects")
def update_issue(issue_id):
    """Update an issue."""
    blocked = _require_module_enabled_for_api("issues")
    if blocked:
        return blocked

    issue = Issue.query.filter_by(id=issue_id).first()
    if not issue:
        return not_found_response("Issue not found")

    data = request.get_json() or {}
    if "title" in data and data["title"] is not None:
        issue.title = str(data["title"]).strip()
    if "description" in data:
        desc = data["description"]
        issue.description = str(desc).strip() if desc else None
    if "status" in data and data["status"] is not None:
        issue.status = str(data["status"]).strip()
    if "priority" in data and data["priority"] is not None:
        issue.priority = str(data["priority"]).strip()
    if "project_id" in data:
        issue.project_id = data["project_id"]
    if "client_id" in data and data["client_id"] is not None:
        issue.client_id = int(data["client_id"])
    if "assigned_to" in data:
        issue.assigned_to = data["assigned_to"]

    db.session.commit()
    return jsonify({"message": "Issue updated successfully", "issue": issue.to_dict()})


@api_v1_issues_bp.route("/issues/<int:issue_id>", methods=["DELETE"])
@require_api_token("write:projects")
def delete_issue(issue_id):
    """Delete an issue."""
    blocked = _require_module_enabled_for_api("issues")
    if blocked:
        return blocked

    if not g.api_user.is_admin:
        return forbidden_response("Only admins can delete issues")

    issue = Issue.query.filter_by(id=issue_id).first()
    if not issue:
        return not_found_response("Issue not found")
    db.session.delete(issue)
    db.session.commit()
    return jsonify({"message": "Issue deleted successfully"})
