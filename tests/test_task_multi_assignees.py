"""Tests for multi-user task assignees."""

import pytest

from app import db
from app.models import Project, Task, TaskAssignee, User
from app.services.task_service import TaskService, normalize_assignee_ids, task_assigned_to_user_clause


@pytest.fixture
def project_and_users(app, test_client):
    """Return IDs so callers can re-load objects inside their own app context."""
    with app.app_context():
        creator = User(username="task_creator_ma", role="user", email="creator_ma@example.com")
        creator.is_active = True
        u1 = User(username="assignee_a", role="user", email="a_ma@example.com")
        u1.is_active = True
        u2 = User(username="assignee_b", role="user", email="b_ma@example.com")
        u2.is_active = True
        db.session.add_all([creator, u1, u2])
        project = Project(name="Multi Assignee Project", client_id=test_client.id, billable=True)
        db.session.add(project)
        db.session.commit()
        return {
            "creator_id": creator.id,
            "u1_id": u1.id,
            "u2_id": u2.id,
            "project_id": project.id,
        }


@pytest.mark.unit
def test_normalize_assignee_ids_dedupes_and_merges_legacy():
    assert normalize_assignee_ids(assignee_ids=[1, 2, 1], assignee_id=2, assigned_to=3) == [1, 2, 3]
    assert normalize_assignee_ids(assignee_id=5) == [5]
    assert normalize_assignee_ids() == []


@pytest.mark.integration
@pytest.mark.models
def test_task_set_assignees_and_is_assigned_to(app, project_and_users):
    with app.app_context():
        data = project_and_users
        task = Task(
            project_id=data["project_id"],
            name="Shared task",
            created_by=data["creator_id"],
            assignee_ids=[data["u1_id"], data["u2_id"]],
        )
        db.session.add(task)
        db.session.commit()

        assert sorted(task.assignee_ids) == sorted([data["u1_id"], data["u2_id"]])
        assert task.is_assigned_to(data["u1_id"])
        assert task.is_assigned_to(data["u2_id"])
        assert not task.is_assigned_to(data["creator_id"])
        assert task.assigned_to in (data["u1_id"], data["u2_id"])
        assert TaskAssignee.query.filter_by(task_id=task.id).count() == 2

        task.set_assignees([data["u1_id"]], commit=True)
        assert task.assignee_ids == [data["u1_id"]]
        assert TaskAssignee.query.filter_by(task_id=task.id).count() == 1


@pytest.mark.integration
@pytest.mark.models
def test_legacy_assigned_to_on_create_migrates_to_links(app, project_and_users):
    with app.app_context():
        data = project_and_users
        task = Task(
            project_id=data["project_id"],
            name="Legacy assign",
            created_by=data["creator_id"],
            assigned_to=data["u1_id"],
        )
        db.session.add(task)
        db.session.commit()
        assert task.assignee_ids == [data["u1_id"]]


@pytest.mark.integration
def test_task_service_create_and_update_assignee_ids(app, project_and_users):
    with app.app_context():
        data = project_and_users
        service = TaskService()
        created = service.create_task(
            name="API multi",
            project_id=data["project_id"],
            created_by=data["creator_id"],
            assignee_ids=[data["u1_id"], data["u2_id"]],
        )
        assert created["success"]
        task = created["task"]
        assert sorted(task.assignee_ids) == sorted([data["u1_id"], data["u2_id"]])

        updated = service.update_task(task.id, data["creator_id"], assignee_ids=[data["u2_id"]])
        assert updated["success"]
        assert updated["task"].assignee_ids == [data["u2_id"]]

        updated2 = service.update_task(task.id, data["creator_id"], assignee_id=data["u1_id"])
        assert updated2["success"]
        assert updated2["task"].assignee_ids == [data["u1_id"]]


@pytest.mark.integration
def test_list_tasks_visibility_for_co_assignee(app, project_and_users):
    with app.app_context():
        data = project_and_users
        service = TaskService()
        service.create_task(
            name="Co assigned",
            project_id=data["project_id"],
            created_by=data["creator_id"],
            assignee_ids=[data["u1_id"], data["u2_id"]],
        )
        result = service.list_tasks(
            user_id=data["u2_id"],
            has_view_all_tasks=False,
            page=1,
            per_page=20,
        )
        names = [t.name for t in result["tasks"]]
        assert "Co assigned" in names

        filtered = service.list_tasks(
            assigned_to_ids=[data["u1_id"]],
            has_view_all_tasks=True,
            page=1,
            per_page=20,
        )
        assert any(t.name == "Co assigned" for t in filtered["tasks"])


@pytest.mark.integration
@pytest.mark.routes
def test_create_task_form_multiple_assignees(authenticated_client, app, project_and_users, user):
    with app.app_context():
        data = project_and_users
        response = authenticated_client.post(
            "/tasks/create",
            data={
                "project_id": data["project_id"],
                "name": "Form multi assignees",
                "priority": "medium",
                "status": "todo",
                "assignee_ids": [str(data["u1_id"]), str(data["u2_id"])],
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        task = Task.query.filter_by(name="Form multi assignees").first()
        assert task is not None
        assert sorted(task.assignee_ids) == sorted([data["u1_id"], data["u2_id"]])


@pytest.mark.integration
@pytest.mark.routes
def test_bulk_assign_replaces_with_multiple_users(authenticated_client, app, project_and_users, user):
    with app.app_context():
        data = project_and_users
        task = Task(
            project_id=data["project_id"],
            name="Bulk target",
            created_by=user.id,
            assigned_to=data["u1_id"],
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

        response = authenticated_client.post(
            "/tasks/bulk-assign",
            data={
                "task_ids[]": [str(task_id)],
                "assignee_ids": [str(data["u1_id"]), str(data["u2_id"])],
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        task = Task.query.get(task_id)
        assert sorted(task.assignee_ids) == sorted([data["u1_id"], data["u2_id"]])


@pytest.mark.integration
@pytest.mark.models
def test_assigned_user_clause(app, project_and_users):
    with app.app_context():
        data = project_and_users
        task = Task(
            project_id=data["project_id"],
            name="Clause task",
            created_by=data["creator_id"],
            assignee_ids=[data["u2_id"]],
        )
        db.session.add(task)
        db.session.commit()
        found = Task.query.filter(task_assigned_to_user_clause(data["u2_id"])).all()
        assert any(t.id == task.id for t in found)
        not_found = Task.query.filter(task_assigned_to_user_clause(data["u1_id"])).all()
        assert all(t.id != task.id for t in not_found)
