"""
Workflow automation routes
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db
from app.models.workflow import WorkflowExecution, WorkflowRule, WorkflowTemplate
from app.routes.workflow_helpers import get_action_types, get_trigger_types, parse_workflow_form_data
from app.services.workflow_engine import WorkflowEngine
from app.services.workflow_template_service import WorkflowTemplateService
from app.utils.decorators import admin_required
from app.utils.module_helpers import module_enabled

workflows_bp = Blueprint("workflows", __name__)
_template_service = WorkflowTemplateService()


def _apply_workflow_fields(rule, fields):
    rule.name = fields["name"]
    rule.description = fields["description"]
    rule.trigger_type = fields["trigger_type"]
    rule.trigger_conditions = fields["trigger_conditions"]
    rule.actions = fields["actions"]
    rule.enabled = fields["enabled"]
    rule.priority = fields["priority"]


@workflows_bp.route("/workflows")
@login_required
@module_enabled("workflows")
def list_workflows():
    """List all workflows"""
    workflows = (
        WorkflowRule.query.filter(WorkflowRule.user_id == current_user.id)
        .order_by(WorkflowRule.priority.desc(), WorkflowRule.created_at.desc())
        .all()
    )

    return render_template("workflows/list.html", workflows=workflows)


@workflows_bp.route("/workflows/create", methods=["GET", "POST"])
@login_required
@module_enabled("workflows")
def create_workflow():
    """Create a new workflow rule"""
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        fields, _, _ = parse_workflow_form_data(data)

        rule = WorkflowRule(user_id=current_user.id, created_by=current_user.id)
        _apply_workflow_fields(rule, fields)
        db.session.add(rule)
        db.session.commit()

        if request.is_json:
            return jsonify({"success": True, "workflow": rule.to_dict()})

        flash(_("Workflow created successfully"), "success")
        return redirect(url_for("workflows.list_workflows"))

    return render_template(
        "workflows/create.html", trigger_types=get_trigger_types(), action_types=get_action_types()
    )


@workflows_bp.route("/workflows/<int:workflow_id>")
@login_required
@module_enabled("workflows")
def view_workflow(workflow_id):
    """View workflow details"""
    workflow = WorkflowRule.query.get_or_404(workflow_id)

    if workflow.user_id != current_user.id and not current_user.is_admin:
        flash(_("Access denied"), "error")
        return redirect(url_for("workflows.list_workflows"))

    executions = (
        WorkflowExecution.query.filter_by(rule_id=workflow_id)
        .order_by(WorkflowExecution.executed_at.desc())
        .limit(50)
        .all()
    )

    return render_template("workflows/view.html", workflow=workflow, executions=executions)


@workflows_bp.route("/workflows/<int:workflow_id>/edit", methods=["GET", "POST"])
@login_required
@module_enabled("workflows")
def edit_workflow(workflow_id):
    """Edit workflow"""
    workflow = WorkflowRule.query.get_or_404(workflow_id)

    if workflow.user_id != current_user.id and not current_user.is_admin:
        flash(_("Access denied"), "error")
        return redirect(url_for("workflows.list_workflows"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        fields, _, _ = parse_workflow_form_data(data)
        _apply_workflow_fields(workflow, fields)
        db.session.commit()

        if request.is_json:
            return jsonify({"success": True, "workflow": workflow.to_dict()})

        flash(_("Workflow updated successfully"), "success")
        return redirect(url_for("workflows.view_workflow", workflow_id=workflow_id))

    return render_template(
        "workflows/edit.html",
        workflow=workflow,
        trigger_types=get_trigger_types(),
        action_types=get_action_types(),
    )


@workflows_bp.route("/workflows/<int:workflow_id>/delete", methods=["POST"])
@login_required
@module_enabled("workflows")
def delete_workflow(workflow_id):
    """Delete workflow"""
    workflow = WorkflowRule.query.get_or_404(workflow_id)

    if workflow.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    db.session.delete(workflow)
    db.session.commit()

    if request.is_json:
        return jsonify({"success": True})

    flash(_("Workflow deleted successfully"), "success")
    return redirect(url_for("workflows.list_workflows"))


@workflows_bp.route("/workflows/<int:workflow_id>/toggle", methods=["POST"])
@login_required
@module_enabled("workflows")
def toggle_workflow(workflow_id):
    """Toggle workflow enabled status"""
    workflow = WorkflowRule.query.get_or_404(workflow_id)

    if workflow.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    workflow.enabled = not workflow.enabled
    db.session.commit()

    return jsonify({"success": True, "enabled": workflow.enabled})


# --- Workflow template library ---


@workflows_bp.route("/workflows/templates")
@login_required
@module_enabled("workflows")
def list_workflow_templates():
    templates = _template_service.list_available(current_user.id, current_user.is_admin)
    return render_template("workflows/templates_list.html", templates=templates)


@workflows_bp.route("/workflows/templates/<int:template_id>/use", methods=["POST"])
@login_required
@module_enabled("workflows")
def use_workflow_template(template_id):
    name = request.form.get("name") or None
    rule = _template_service.clone_to_rule(template_id, current_user.id, name=name)
    flash(_("Workflow created from template"), "success")
    return redirect(url_for("workflows.edit_workflow", workflow_id=rule.id))


@workflows_bp.route("/workflows/templates/create", methods=["GET", "POST"])
@login_required
@module_enabled("workflows")
@admin_required
def create_workflow_template():
    if request.method == "POST":
        data = request.form
        fields, _, _ = parse_workflow_form_data(data)
        _template_service.create_template(
            {
                **fields,
                "category": data.get("category"),
                "tags": [t.strip() for t in (data.get("tags") or "").split(",") if t.strip()],
                "is_public": data.get("is_public") == "on",
            },
            current_user.id,
        )
        flash(_("Workflow template created"), "success")
        return redirect(url_for("workflows.list_workflow_templates"))

    return render_template(
        "workflows/template_form.html",
        template=None,
        trigger_types=get_trigger_types(),
        action_types=get_action_types(),
        form_action=url_for("workflows.create_workflow_template"),
        submit_label=_("Create Template"),
    )


@workflows_bp.route("/workflows/templates/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
@module_enabled("workflows")
@admin_required
def edit_workflow_template(template_id):
    template = WorkflowTemplate.query.get_or_404(template_id)
    if request.method == "POST":
        data = request.form
        fields, _, _ = parse_workflow_form_data(data)
        _template_service.update_template(
            template,
            {
                **fields,
                "category": data.get("category"),
                "tags": [t.strip() for t in (data.get("tags") or "").split(",") if t.strip()],
                "is_public": data.get("is_public") == "on",
            },
        )
        flash(_("Workflow template updated"), "success")
        return redirect(url_for("workflows.list_workflow_templates"))

    return render_template(
        "workflows/template_form.html",
        template=template,
        trigger_types=get_trigger_types(),
        action_types=get_action_types(),
        form_action=url_for("workflows.edit_workflow_template", template_id=template.id),
        submit_label=_("Save Template"),
    )


@workflows_bp.route("/workflows/templates/<int:template_id>/delete", methods=["POST"])
@login_required
@module_enabled("workflows")
@admin_required
def delete_workflow_template(template_id):
    template = WorkflowTemplate.query.get_or_404(template_id)
    _template_service.delete_template(template)
    flash(_("Workflow template deleted"), "success")
    return redirect(url_for("workflows.list_workflow_templates"))


# --- API ---


@workflows_bp.route("/api/workflows", methods=["GET"])
@login_required
@module_enabled("workflows")
def api_list_workflows():
    """API: List workflows"""
    workflows = WorkflowRule.query.filter(WorkflowRule.user_id == current_user.id).all()
    return jsonify({"workflows": [w.to_dict() for w in workflows]})


@workflows_bp.route("/api/workflows", methods=["POST"])
@login_required
@module_enabled("workflows")
def api_create_workflow():
    """API: Create workflow"""
    data = request.get_json()

    rule = WorkflowRule(
        name=data.get("name"),
        description=data.get("description"),
        trigger_type=data.get("trigger_type"),
        trigger_conditions=data.get("trigger_conditions"),
        actions=data.get("actions", []),
        enabled=data.get("enabled", True),
        priority=data.get("priority", 0),
        user_id=current_user.id,
        created_by=current_user.id,
    )

    db.session.add(rule)
    db.session.commit()

    return jsonify({"success": True, "workflow": rule.to_dict()}), 201


@workflows_bp.route("/api/workflows/<int:workflow_id>", methods=["GET"])
@login_required
@module_enabled("workflows")
def api_get_workflow(workflow_id):
    """API: Get workflow"""
    workflow = WorkflowRule.query.get_or_404(workflow_id)

    if workflow.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    return jsonify({"workflow": workflow.to_dict()})


@workflows_bp.route("/api/workflows/<int:workflow_id>", methods=["PUT"])
@login_required
@module_enabled("workflows")
def api_update_workflow(workflow_id):
    """API: Update workflow"""
    workflow = WorkflowRule.query.get_or_404(workflow_id)

    if workflow.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()

    workflow.name = data.get("name", workflow.name)
    workflow.description = data.get("description", workflow.description)
    workflow.trigger_type = data.get("trigger_type", workflow.trigger_type)
    workflow.trigger_conditions = data.get("trigger_conditions", workflow.trigger_conditions)
    workflow.actions = data.get("actions", workflow.actions)
    workflow.enabled = data.get("enabled", workflow.enabled)
    workflow.priority = data.get("priority", workflow.priority)

    db.session.commit()

    return jsonify({"success": True, "workflow": workflow.to_dict()})


@workflows_bp.route("/api/workflows/<int:workflow_id>", methods=["DELETE"])
@login_required
@module_enabled("workflows")
def api_delete_workflow(workflow_id):
    """API: Delete workflow"""
    workflow = WorkflowRule.query.get_or_404(workflow_id)

    if workflow.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    db.session.delete(workflow)
    db.session.commit()

    return jsonify({"success": True})


@workflows_bp.route("/api/workflows/<int:workflow_id>/test", methods=["POST"])
@login_required
@module_enabled("workflows")
def test_workflow(workflow_id):
    """Test workflow with sample event"""
    workflow = WorkflowRule.query.get_or_404(workflow_id)

    if workflow.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    test_event = data.get("event", {"type": workflow.trigger_type, "data": {"user_id": current_user.id}})

    result = WorkflowEngine.execute_rule(workflow, test_event)

    return jsonify(result)
