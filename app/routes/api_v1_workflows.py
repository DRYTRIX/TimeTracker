"""API v1 - Workflow templates and run history."""

from flask import Blueprint, g, jsonify, request

from app.models.workflow import WorkflowExecution, WorkflowRule
from app.services.workflow_template_service import WorkflowTemplateService
from app.utils.api_auth import require_api_token
from app.utils.api_responses import not_found_response

api_v1_workflows_bp = Blueprint("api_v1_workflows", __name__, url_prefix="/api/v1")
_template_service = WorkflowTemplateService()


@api_v1_workflows_bp.route("/workflows/templates", methods=["GET"])
@require_api_token("read:projects")
def list_workflow_templates():
    """List available workflow templates for the token user."""
    templates = _template_service.list_available(g.api_user.id, g.api_user.is_admin)
    return jsonify({"templates": [t.to_dict() for t in templates]})


@api_v1_workflows_bp.route("/workflows/templates/<int:template_id>", methods=["GET"])
@require_api_token("read:projects")
def get_workflow_template(template_id):
    """Get a single workflow template if visible to the user."""
    template = _template_service.get_template(template_id)
    if not template:
        return not_found_response("Workflow template not found")
    if not template.is_public and template.created_by != g.api_user.id and not g.api_user.is_admin:
        return not_found_response("Workflow template not found")
    return jsonify({"template": template.to_dict()})


@api_v1_workflows_bp.route("/workflows/executions", methods=["GET"])
@require_api_token("read:projects")
def list_workflow_executions():
    """List recent workflow run history for the user's rules (or all if admin)."""
    rule_id = request.args.get("rule_id", type=int)
    limit = request.args.get("limit", 50, type=int)
    limit = max(1, min(limit or 50, 200))

    query = WorkflowExecution.query.join(WorkflowRule)
    if not g.api_user.is_admin:
        query = query.filter(WorkflowRule.user_id == g.api_user.id)
    if rule_id:
        query = query.filter(WorkflowExecution.rule_id == rule_id)

    executions = query.order_by(WorkflowExecution.executed_at.desc()).limit(limit).all()
    return jsonify({"executions": [e.to_dict() for e in executions]})
