"""API v1 - Project templates."""

from flask import Blueprint, g, jsonify

from app.models import ProjectTemplate
from app.utils.api_auth import require_api_token
from app.utils.api_responses import not_found_response

api_v1_project_templates_bp = Blueprint("api_v1_project_templates", __name__, url_prefix="/api/v1")


@api_v1_project_templates_bp.route("/project-templates", methods=["GET"])
@require_api_token("read:projects")
def list_project_templates():
    """List project templates visible to the user."""
    if g.api_user.is_admin:
        items = ProjectTemplate.query.order_by(ProjectTemplate.name.asc()).limit(200).all()
    else:
        items = (
            ProjectTemplate.query.filter(
                (ProjectTemplate.is_public == True) | (ProjectTemplate.created_by == g.api_user.id)  # noqa: E712
            )
            .order_by(ProjectTemplate.name.asc())
            .limit(200)
            .all()
        )
    return jsonify({"project_templates": [t.to_dict() for t in items]})


@api_v1_project_templates_bp.route("/project-templates/<int:template_id>", methods=["GET"])
@require_api_token("read:projects")
def get_project_template(template_id):
    """Get a project template."""
    item = ProjectTemplate.query.get(template_id)
    if not item:
        return not_found_response("Project template not found")
    if not g.api_user.is_admin and not item.is_public and item.created_by != g.api_user.id:
        return not_found_response("Project template not found")
    return jsonify({"project_template": item.to_dict()})
