"""Tests for workflow engine, bridge, and templates."""

import pytest

from app import db
from app.models.workflow import WorkflowExecution, WorkflowRule, WorkflowTemplate
from app.services.workflow_engine import WorkflowEngine
from app.services.workflow_template_service import WorkflowTemplateService
from app.utils.workflow_bridge import WEBHOOK_TO_WORKFLOW, trigger_workflow_event
from factories import UserFactory


@pytest.fixture
def workflow_user(app):
    with app.app_context():
        user = UserFactory()
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        yield user
        WorkflowExecution.query.filter(
            WorkflowExecution.rule_id.in_(db.session.query(WorkflowRule.id).filter_by(user_id=user.id))
        ).delete(synchronize_session=False)
        WorkflowRule.query.filter_by(user_id=user.id).delete()
        WorkflowTemplate.query.filter_by(created_by=user.id).delete()
        db.session.delete(user)
        db.session.commit()


def test_webhook_to_workflow_mapping():
    assert WEBHOOK_TO_WORKFLOW["task.created"] == "task_created"
    assert WEBHOOK_TO_WORKFLOW["invoice.paid"] == "invoice_paid"


def test_trigger_event_scoped_to_user(app, workflow_user):
    with app.app_context():
        other = UserFactory()
        db.session.add(other)
        db.session.commit()

        rule_owner = WorkflowRule(
            name="Owner rule",
            trigger_type="task_completed",
            actions=[{"type": "send_notification", "title": "Done", "message": "ok"}],
            user_id=workflow_user.id,
            created_by=workflow_user.id,
        )
        rule_other = WorkflowRule(
            name="Other rule",
            trigger_type="task_completed",
            actions=[{"type": "send_notification", "title": "Other", "message": "no"}],
            user_id=other.id,
            created_by=other.id,
        )
        db.session.add_all([rule_owner, rule_other])
        db.session.commit()

        results = WorkflowEngine.trigger_event(
            "task_completed",
            {"user_id": workflow_user.id, "task": {"name": "Test"}},
        )
        assert len(results) == 1
        assert results[0]["rule_id"] == rule_owner.id

        WorkflowExecution.query.filter_by(rule_id=rule_owner.id).delete()
        WorkflowExecution.query.filter_by(rule_id=rule_other.id).delete()
        db.session.delete(rule_owner)
        db.session.delete(rule_other)
        db.session.delete(other)
        db.session.commit()


def test_workflow_template_clone(app, workflow_user):
    with app.app_context():
        service = WorkflowTemplateService()
        template = service.create_template(
            {
                "name": "Notify template",
                "trigger_type": "invoice_paid",
                "actions": [{"type": "send_notification", "title": "Paid", "message": "done"}],
                "is_public": True,
            },
            workflow_user.id,
        )
        rule = service.clone_to_rule(template.id, workflow_user.id)
        assert rule.name == template.name
        assert rule.trigger_type == "invoice_paid"
        assert template.usage_count == 1


def test_workflow_bridge_task_created(app, workflow_user):
    with app.app_context():
        rule = WorkflowRule(
            name="On create",
            trigger_type="task_created",
            actions=[{"type": "send_notification", "title": "New", "message": "task"}],
            user_id=workflow_user.id,
            created_by=workflow_user.id,
        )
        db.session.add(rule)
        db.session.commit()

        trigger_workflow_event("task.created", {"user_id": workflow_user.id, "task_id": 1})
        updated = WorkflowRule.query.get(rule.id)
        assert updated is not None
