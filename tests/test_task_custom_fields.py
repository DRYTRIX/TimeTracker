"""Task custom fields saved from the create form."""

import pytest

from app import db
from app.models import CustomFieldDefinition, Task

pytestmark = [pytest.mark.integration, pytest.mark.routes]


def test_task_create_saves_custom_fields(app, authenticated_client, project, user):
    """POST /tasks/create persists task-scoped custom field values."""
    with app.app_context():
        definition = CustomFieldDefinition(
            field_key="task_cf_sprint",
            entity_type="task",
            label="Sprint",
            created_by=user.id,
            is_active=True,
        )
        db.session.add(definition)
        db.session.commit()

    resp = authenticated_client.post(
        "/tasks/create",
        data={
            "project_id": str(project.id),
            "name": "Task With CF",
            "status": "todo",
            "custom_field_task_cf_sprint": "Sprint 42",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    with app.app_context():
        task = Task.query.filter_by(name="Task With CF", project_id=project.id).first()
        assert task is not None
        assert task.custom_fields == {"task_cf_sprint": "Sprint 42"}
