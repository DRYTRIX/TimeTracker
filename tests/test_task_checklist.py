"""Per-task checklists / subtasks."""

import pytest

from app import db
from app.models import Project, Task, TaskChecklistItem

pytestmark = [pytest.mark.integration, pytest.mark.routes]


@pytest.fixture
def checklist_task(app, admin_user, test_client):
    """A task owned by the admin user, for checklist tests."""
    with app.app_context():
        project = Project(
            name="Checklist Project",
            client_id=test_client.id,
            status="active",
            created_by=admin_user.id,
        )
        db.session.add(project)
        db.session.commit()

        task = Task(project_id=project.id, name="Checklist Task", created_by=admin_user.id)
        db.session.add(task)
        db.session.commit()
        return task.id


def test_checklist_item_roundtrip_and_to_dict(app, checklist_task):
    with app.app_context():
        item = TaskChecklistItem(task_id=checklist_task, text="  Write tests  ", position=0)
        db.session.add(item)
        db.session.commit()

        stored = TaskChecklistItem.query.filter_by(task_id=checklist_task).first()
        assert stored.text == "Write tests"  # trimmed
        assert stored.is_done is False
        d = stored.to_dict()
        assert d["text"] == "Write tests"
        assert d["is_done"] is False
        assert d["task_id"] == checklist_task


def test_task_checklist_progress_properties(app, checklist_task):
    with app.app_context():
        task = Task.query.get(checklist_task)
        assert task.checklist_total == 0
        assert task.checklist_progress == 0  # no divide-by-zero

        db.session.add(TaskChecklistItem(task_id=checklist_task, text="a", position=0, is_done=True))
        db.session.add(TaskChecklistItem(task_id=checklist_task, text="b", position=1, is_done=False))
        db.session.add(TaskChecklistItem(task_id=checklist_task, text="c", position=2, is_done=False))
        db.session.commit()

        task = Task.query.get(checklist_task)
        assert task.checklist_total == 3
        assert task.checklist_done == 1
        assert task.checklist_progress == 33


def test_add_checklist_item_route(app, admin_authenticated_client, checklist_task):
    resp = admin_authenticated_client.post(
        f"/tasks/{checklist_task}/checklist",
        data={"text": "First item"},
    )
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["success"] is True
    assert payload["item"]["text"] == "First item"
    assert payload["checklist"]["total"] == 1
    assert payload["checklist"]["done"] == 0

    with app.app_context():
        assert TaskChecklistItem.query.filter_by(task_id=checklist_task).count() == 1


def test_add_checklist_item_requires_text(app, admin_authenticated_client, checklist_task):
    resp = admin_authenticated_client.post(f"/tasks/{checklist_task}/checklist", data={"text": "   "})
    assert resp.status_code == 400


def test_toggle_checklist_item_route(app, admin_authenticated_client, checklist_task):
    with app.app_context():
        item = TaskChecklistItem(task_id=checklist_task, text="toggle me", position=0)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    resp = admin_authenticated_client.post(f"/tasks/checklist/{item_id}/toggle")
    assert resp.status_code == 200
    assert resp.get_json()["item"]["is_done"] is True
    assert resp.get_json()["checklist"]["progress"] == 100

    # Toggle back.
    resp = admin_authenticated_client.post(f"/tasks/checklist/{item_id}/toggle")
    assert resp.get_json()["item"]["is_done"] is False


def test_edit_checklist_item_route(app, admin_authenticated_client, checklist_task):
    with app.app_context():
        item = TaskChecklistItem(task_id=checklist_task, text="old", position=0)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    resp = admin_authenticated_client.post(f"/tasks/checklist/{item_id}/edit", data={"text": "new text"})
    assert resp.status_code == 200
    assert resp.get_json()["item"]["text"] == "new text"
    with app.app_context():
        assert TaskChecklistItem.query.get(item_id).text == "new text"


def test_delete_checklist_item_route(app, admin_authenticated_client, checklist_task):
    with app.app_context():
        item = TaskChecklistItem(task_id=checklist_task, text="doomed", position=0)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    resp = admin_authenticated_client.post(f"/tasks/checklist/{item_id}/delete")
    assert resp.status_code == 200
    assert resp.get_json()["checklist"]["total"] == 0
    with app.app_context():
        assert TaskChecklistItem.query.get(item_id) is None


def test_reorder_checklist_items_route(app, admin_authenticated_client, checklist_task):
    with app.app_context():
        a = TaskChecklistItem(task_id=checklist_task, text="a", position=0)
        b = TaskChecklistItem(task_id=checklist_task, text="b", position=1)
        c = TaskChecklistItem(task_id=checklist_task, text="c", position=2)
        db.session.add_all([a, b, c])
        db.session.commit()
        ids = [a.id, b.id, c.id]

    # Reverse order.
    resp = admin_authenticated_client.post(
        f"/tasks/{checklist_task}/checklist/reorder",
        data={"item_ids[]": [ids[2], ids[1], ids[0]]},
    )
    assert resp.status_code == 200
    with app.app_context():
        task = Task.query.get(checklist_task)
        assert [i.id for i in task.checklist_items] == [ids[2], ids[1], ids[0]]


def test_checklist_cascade_delete_with_task(app, checklist_task):
    """Deleting a task removes its checklist items."""
    with app.app_context():
        db.session.add(TaskChecklistItem(task_id=checklist_task, text="x", position=0))
        db.session.commit()
        task = Task.query.get(checklist_task)
        db.session.delete(task)
        db.session.commit()
        assert TaskChecklistItem.query.filter_by(task_id=checklist_task).count() == 0


def test_task_view_renders_checklist_card(app, admin_authenticated_client, checklist_task):
    """The task detail page renders the checklist card without template errors."""
    with app.app_context():
        db.session.add(TaskChecklistItem(task_id=checklist_task, text="render me", position=0))
        db.session.commit()

    resp = admin_authenticated_client.get(f"/tasks/{checklist_task}")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "checklistCard" in body
    assert "render me" in body
