"""Bridge domain events to workflow automation engine."""

from typing import Any, Dict, Optional

from flask import has_app_context

from app.constants import WebhookEvent

WEBHOOK_TO_WORKFLOW = {
    WebhookEvent.TASK_CREATED.value: "task_created",
    WebhookEvent.INVOICE_CREATED.value: "invoice_created",
    WebhookEvent.INVOICE_PAID.value: "invoice_paid",
}


def _task_payload(task, user_id: int, old_status: Optional[str] = None) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "task_id": task.id,
        "project_id": task.project_id,
        "old_status": old_status,
        "new_status": task.status,
        "task": {
            "id": task.id,
            "name": task.name,
            "status": task.status,
            "project_id": task.project_id,
            "assigned_to": task.assigned_to,
        },
    }


def _invoice_payload(invoice, user_id: int) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "invoice_id": invoice.id,
        "project_id": invoice.project_id,
        "client_id": invoice.client_id,
        "invoice": {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "total_amount": float(invoice.total_amount or 0),
            "status": invoice.status,
            "payment_status": invoice.payment_status,
        },
    }


def _time_entry_payload(entry, user_id: int) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "entry_id": entry.id,
        "project_id": entry.project_id,
        "client_id": entry.client_id,
        "task_id": entry.task_id,
        "duration_seconds": entry.duration_seconds,
    }


def trigger_workflow_event(event_type: str, data: Dict[str, Any], workflow_type: Optional[str] = None) -> None:
    """Trigger workflow rules for a domain event."""
    if not has_app_context():
        return

    from app.services.workflow_engine import WorkflowEngine

    resolved_type = workflow_type or WEBHOOK_TO_WORKFLOW.get(event_type)
    if not resolved_type:
        return

    payload = dict(data or {})
    if "user_id" not in payload and payload.get("created_by"):
        payload["user_id"] = payload["created_by"]

    try:
        WorkflowEngine.trigger_event(resolved_type, payload)
    except Exception as exc:
        from flask import current_app

        current_app.logger.error("Workflow trigger failed for %s: %s", resolved_type, exc, exc_info=True)


def handle_domain_event_for_workflows(event_type: str, data: Dict[str, Any]) -> None:
    """Event bus handler that maps webhook events to workflow triggers."""
    trigger_workflow_event(event_type, data)


def fire_task_status_workflows(task, user_id: int, old_status: Optional[str] = None) -> None:
    payload = _task_payload(task, user_id, old_status=old_status)
    trigger_workflow_event("task_status_change", payload, workflow_type="task_status_change")
    if task.status == "done":
        trigger_workflow_event("task_completed", payload, workflow_type="task_completed")


def fire_time_logged_workflow(entry, user_id: int) -> None:
    trigger_workflow_event("time_logged", _time_entry_payload(entry, user_id), workflow_type="time_logged")


def fire_invoice_created_workflow(invoice, user_id: int) -> None:
    from app.constants import WebhookEvent

    payload = _invoice_payload(invoice, user_id)
    trigger_workflow_event(WebhookEvent.INVOICE_CREATED.value, payload)
    trigger_workflow_event("invoice_created", payload, workflow_type="invoice_created")


def fire_invoice_paid_workflow(invoice, user_id: int) -> None:
    from app.constants import WebhookEvent

    payload = _invoice_payload(invoice, user_id)
    trigger_workflow_event(WebhookEvent.INVOICE_PAID.value, payload)
    trigger_workflow_event("invoice_paid", payload, workflow_type="invoice_paid")


def fire_budget_threshold_workflow(project, alert_data: Dict[str, Any], user_id: Optional[int] = None) -> None:
    owner_id = user_id or getattr(project, "created_by", None) or alert_data.get("user_id")
    if not owner_id:
        return
    trigger_workflow_event(
        "budget_threshold",
        {
            "user_id": owner_id,
            "project_id": project.id,
            "project": {"id": project.id, "name": project.name},
            **alert_data,
        },
        workflow_type="budget_threshold",
    )


def fire_deadline_approaching_workflow(task, user_id: int) -> None:
    trigger_workflow_event(
        "deadline_approaching",
        _task_payload(task, user_id),
        workflow_type="deadline_approaching",
    )
