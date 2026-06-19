"""Tests for the domain-event -> workflow-engine bridge.

Verifies the fan-out logic in app/utils/workflow_bridge.py (which event types
get triggered, payload shaping, and error isolation) without standing up real
workflow rules. WorkflowEngine.trigger_event is mocked so we assert on the
resolved workflow type and payload passed to the engine.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.integration]

from app.constants import WebhookEvent
from app.utils import workflow_bridge as wb


def _task(status="in_progress", **kw):
    defaults = dict(id=1, name="Task", status=status, project_id=10, assigned_to=None)
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _invoice(**kw):
    defaults = dict(
        id=5,
        invoice_number="INV-001",
        total_amount=100,
        status="sent",
        payment_status="paid",
        project_id=10,
        client_id=3,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _resolved_types(mock):
    """Return the resolved workflow type from each trigger_event call."""
    return [call.args[0] for call in mock.call_args_list]


def test_unknown_event_without_workflow_type_does_not_trigger(app):
    with patch("app.services.workflow_engine.WorkflowEngine.trigger_event") as m:
        wb.trigger_workflow_event("some.unmapped.event", {"user_id": 1})
    m.assert_not_called()


def test_trigger_defaults_user_id_from_created_by(app):
    with patch("app.services.workflow_engine.WorkflowEngine.trigger_event") as m:
        wb.trigger_workflow_event("custom", {"created_by": 42}, workflow_type="custom")
    assert m.call_count == 1
    payload = m.call_args.args[1]
    assert payload["user_id"] == 42


def test_invoice_paid_fires_invoice_paid_workflow_twice(app):
    with patch("app.services.workflow_engine.WorkflowEngine.trigger_event") as m:
        wb.fire_invoice_paid_workflow(_invoice(), user_id=1)
    # Once via the webhook->workflow mapping, once via the explicit workflow_type
    assert _resolved_types(m) == ["invoice_paid", "invoice_paid"]
    # WEBHOOK_TO_WORKFLOW must map the webhook event to the workflow type
    assert wb.WEBHOOK_TO_WORKFLOW[WebhookEvent.INVOICE_PAID.value] == "invoice_paid"


def test_task_status_change_does_not_fire_completed(app):
    with patch("app.services.workflow_engine.WorkflowEngine.trigger_event") as m:
        wb.fire_task_status_workflows(_task(status="in_progress"), user_id=1, old_status="todo")
    assert _resolved_types(m) == ["task_status_change"]


def test_task_done_also_fires_completed(app):
    with patch("app.services.workflow_engine.WorkflowEngine.trigger_event") as m:
        wb.fire_task_status_workflows(_task(status="done"), user_id=1, old_status="in_progress")
    assert _resolved_types(m) == ["task_status_change", "task_completed"]


def test_budget_threshold_without_owner_is_skipped(app):
    project = SimpleNamespace(id=10, name="P", created_by=None)
    with patch("app.services.workflow_engine.WorkflowEngine.trigger_event") as m:
        wb.fire_budget_threshold_workflow(project, alert_data={"threshold": 80}, user_id=None)
    m.assert_not_called()


def test_budget_threshold_with_owner_merges_payload(app):
    project = SimpleNamespace(id=10, name="P", created_by=7)
    with patch("app.services.workflow_engine.WorkflowEngine.trigger_event") as m:
        wb.fire_budget_threshold_workflow(project, alert_data={"threshold": 80}, user_id=None)
    assert m.call_count == 1
    resolved, payload = m.call_args.args
    assert resolved == "budget_threshold"
    assert payload["user_id"] == 7
    assert payload["project_id"] == 10
    assert payload["threshold"] == 80


def test_trigger_isolates_engine_errors(app):
    """A failing engine call must not propagate out of the bridge."""
    with patch(
        "app.services.workflow_engine.WorkflowEngine.trigger_event",
        side_effect=RuntimeError("boom"),
    ):
        # Should log and swallow, not raise
        wb.fire_invoice_created_workflow(_invoice(), user_id=1)
