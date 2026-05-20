"""Kanban board respects view_own_tasks scope (issue #641)."""

import pytest

from app import db
from app.models import KanbanColumn, Project, Task, User
from app.utils.permissions_seed import seed_permissions, seed_roles

pytestmark = [pytest.mark.integration, pytest.mark.routes]


@pytest.fixture
def kanban_own_user(app):
    with app.app_context():
        seed_permissions()
        seed_roles(silent=True)
        from app.models import Role

        role = Role.query.filter_by(name="user").first()
        user = User.query.filter_by(username="kanban_own_user").first()
        if not user:
            user = User(username="kanban_own_user", email="kanbanown@example.com", role="user")
            user.is_active = True
            user.set_password("password123")
            db.session.add(user)
        if role and role not in user.roles:
            user.roles.append(role)
        db.session.commit()
        return user.id


def test_kanban_hides_other_users_tasks(app, client, test_client, kanban_own_user):
    """User with view_own_tasks only does not see tasks assigned to others on /kanban."""
    with app.app_context():
        owner = User.query.get(kanban_own_user)
        other = User.query.filter_by(username="other_kanban_user").first()
        if not other:
            other = User(username="other_kanban_user", email="otherkanban@example.com", role="user")
            other.is_active = True
            other.set_password("password123")
            db.session.add(other)
            db.session.commit()

        project = Project.query.filter_by(client_id=test_client.id).first()
        if not project:
            project = Project(
                name="Kanban Test Project",
                client_id=test_client.id,
                status="active",
                created_by=owner.id,
            )
            db.session.add(project)
            db.session.commit()

        if not KanbanColumn.query.filter_by(project_id=None).first():
            KanbanColumn.initialize_default_columns(project_id=None)

        my_task = Task(
            name="My Kanban Task",
            project_id=project.id,
            created_by=owner.id,
            assigned_to=owner.id,
            status="todo",
        )
        other_task = Task(
            name="Other Kanban Task",
            project_id=project.id,
            created_by=other.id,
            assigned_to=other.id,
            status="todo",
        )
        db.session.add_all([my_task, other_task])
        db.session.commit()
        my_id, other_id = my_task.id, other_task.id

    client.post("/login", data={"username": "kanban_own_user", "password": "password123"}, follow_redirects=True)
    resp = client.get("/kanban")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert str(my_id) in body or "My Kanban Task" in body
    assert "Other Kanban Task" not in body
