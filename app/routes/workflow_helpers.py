"""Shared helpers for workflow routes."""

import json
from typing import Any, Dict, List, Tuple

from flask_babel import gettext as _


def get_trigger_types() -> List[Dict[str, str]]:
    return [
        {"value": "task_status_change", "label": _("Task Status Changes")},
        {"value": "task_created", "label": _("Task Created")},
        {"value": "task_completed", "label": _("Task Completed")},
        {"value": "time_logged", "label": _("Time Logged")},
        {"value": "deadline_approaching", "label": _("Deadline Approaching")},
        {"value": "budget_threshold", "label": _("Budget Threshold Reached")},
        {"value": "invoice_created", "label": _("Invoice Created")},
        {"value": "invoice_paid", "label": _("Invoice Paid")},
    ]


def get_action_types() -> List[Dict[str, str]]:
    return [
        {"value": "log_time", "label": _("Log Time Entry")},
        {"value": "send_notification", "label": _("Send Notification")},
        {"value": "update_status", "label": _("Update Status")},
        {"value": "assign_task", "label": _("Assign Task")},
        {"value": "create_task", "label": _("Create Task")},
        {"value": "update_project", "label": _("Update Project")},
        {"value": "send_email", "label": _("Send Email")},
        {"value": "webhook", "label": _("Trigger Webhook")},
    ]


def parse_workflow_form_data(data) -> Tuple[Dict[str, Any], List[Dict[str, Any]], bool]:
    """Parse workflow form/JSON data into rule fields."""
    enabled_raw = data.get("enabled", True)
    if isinstance(enabled_raw, str):
        enabled = enabled_raw.lower() in ("true", "1", "on", "yes")
    else:
        enabled = bool(enabled_raw)

    try:
        priority = int(data.get("priority", 0) or 0)
    except (TypeError, ValueError):
        priority = 0

    trigger_conditions = data.get("trigger_conditions")
    if isinstance(trigger_conditions, str):
        trigger_conditions = json.loads(trigger_conditions) if trigger_conditions.strip() else []
    elif trigger_conditions is None:
        trigger_conditions = []

    actions = data.get("actions")
    if isinstance(actions, str):
        actions = json.loads(actions) if actions.strip() else []
    elif actions is None:
        actions = []

    if not isinstance(trigger_conditions, list):
        trigger_conditions = [trigger_conditions] if trigger_conditions else []
    if not isinstance(actions, list):
        actions = [actions] if actions else []

    fields = {
        "name": data.get("name"),
        "description": data.get("description"),
        "trigger_type": data.get("trigger_type"),
        "trigger_conditions": trigger_conditions,
        "actions": actions,
        "enabled": enabled,
        "priority": priority,
    }
    return fields, actions, enabled
