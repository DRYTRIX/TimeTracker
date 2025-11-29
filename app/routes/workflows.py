"""
Workflow automation routes
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.workflow import WorkflowRule, WorkflowExecution
from app.services.workflow_engine import WorkflowEngine
from app.utils.decorators import admin_required
from flask_babel import gettext as _

workflows_bp = Blueprint("workflows", __name__)


@workflows_bp.route("/workflows")
@login_required
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
def create_workflow():
    """Create a new workflow rule"""
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form

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

        if request.is_json:
            return jsonify({"success": True, "workflow": rule.to_dict()})

        flash(_("Workflow created successfully"), "success")
        return redirect(url_for("workflows.list_workflows"))

    # GET - Show form
    trigger_types = [
        {"value": "task_status_change", "label": _("Task Status Changes")},
        {"value": "task_created", "label": _("Task Created")},
        {"value": "task_completed", "label": _("Task Completed")},
        {"value": "time_logged", "label": _("Time Logged")},
        {"value": "deadline_approaching", "label": _("Deadline Approaching")},
        {"value": "budget_threshold", "label": _("Budget Threshold Reached")},
        {"value": "invoice_created", "label": _("Invoice Created")},
        {"value": "invoice_paid", "label": _("Invoice Paid")},
    ]

    action_types = [
        {"value": "log_time", "label": _("Log Time Entry")},
        {"value": "send_notification", "label": _("Send Notification")},
        {"value": "update_status", "label": _("Update Status")},
        {"value": "assign_task", "label": _("Assign Task")},
        {"value": "create_task", "label": _("Create Task")},
        {"value": "update_project", "label": _("Update Project")},
        {"value": "send_email", "label": _("Send Email")},
        {"value": "webhook", "label": _("Trigger Webhook")},
    ]

    return render_template("workflows/create.html", trigger_types=trigger_types, action_types=action_types)


@workflows_bp.route("/workflows/<int:workflow_id>")
@login_required
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
def edit_workflow(workflow_id):
    """Edit workflow"""
    workflow = WorkflowRule.query.get_or_404(workflow_id)

    if workflow.user_id != current_user.id and not current_user.is_admin:
        flash(_("Access denied"), "error")
        return redirect(url_for("workflows.list_workflows"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form

        workflow.name = data.get("name", workflow.name)
        workflow.description = data.get("description", workflow.description)
        workflow.trigger_type = data.get("trigger_type", workflow.trigger_type)
        workflow.trigger_conditions = data.get("trigger_conditions", workflow.trigger_conditions)
        workflow.actions = data.get("actions", workflow.actions)
        workflow.enabled = data.get("enabled", workflow.enabled)
        workflow.priority = data.get("priority", workflow.priority)

        db.session.commit()

        if request.is_json:
            return jsonify({"success": True, "workflow": workflow.to_dict()})

        flash(_("Workflow updated successfully"), "success")
        return redirect(url_for("workflows.view_workflow", workflow_id=workflow_id))

    trigger_types = [
        {"value": "task_status_change", "label": _("Task Status Changes")},
        {"value": "task_created", "label": _("Task Created")},
        {"value": "task_completed", "label": _("Task Completed")},
        {"value": "time_logged", "label": _("Time Logged")},
        {"value": "deadline_approaching", "label": _("Deadline Approaching")},
        {"value": "budget_threshold", "label": _("Budget Threshold Reached")},
    ]

    action_types = [
        {"value": "log_time", "label": _("Log Time Entry")},
        {"value": "send_notification", "label": _("Send Notification")},
        {"value": "update_status", "label": _("Update Status")},
        {"value": "assign_task", "label": _("Assign Task")},
    ]

    return render_template(
        "workflows/edit.html", workflow=workflow, trigger_types=trigger_types, action_types=action_types
    )


@workflows_bp.route("/workflows/<int:workflow_id>/delete", methods=["POST"])
@login_required
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
def toggle_workflow(workflow_id):
    """Toggle workflow enabled status"""
    workflow = WorkflowRule.query.get_or_404(workflow_id)

    if workflow.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    workflow.enabled = not workflow.enabled
    db.session.commit()

    return jsonify({"success": True, "enabled": workflow.enabled})


@workflows_bp.route("/api/workflows", methods=["GET"])
@login_required
def api_list_workflows():
    """API: List workflows"""
    workflows = WorkflowRule.query.filter(WorkflowRule.user_id == current_user.id).all()
    return jsonify({"workflows": [w.to_dict() for w in workflows]})


@workflows_bp.route("/api/workflows", methods=["POST"])
@login_required
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
def api_get_workflow(workflow_id):
    """API: Get workflow"""
    workflow = WorkflowRule.query.get_or_404(workflow_id)

    if workflow.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    return jsonify({"workflow": workflow.to_dict()})


@workflows_bp.route("/api/workflows/<int:workflow_id>", methods=["PUT"])
@login_required
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
def test_workflow(workflow_id):
    """Test workflow with sample event"""
    workflow = WorkflowRule.query.get_or_404(workflow_id)

    if workflow.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    test_event = data.get("event", {"type": workflow.trigger_type, "data": {}})

    result = WorkflowEngine.execute_rule(workflow, test_event)

    return jsonify(result)
