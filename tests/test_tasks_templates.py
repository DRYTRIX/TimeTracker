import pytest

from app import db
from app.models import User, Project, Task


@pytest.mark.smoke
@pytest.mark.routes
def test_create_task_page_has_tips(client, app):
    with app.app_context():
        # Minimal data to render page
        user = User(username="ui_user", role="user")
        user.is_active = True
        db.session.add(user)
        db.session.add(Project(name="UI Test Project", client="UI Test Client"))
        db.session.commit()

        # Login using the login endpoint
        client.post("/login", data={"username": user.username}, follow_redirects=True)

        resp = client.get("/tasks/create")
        assert resp.status_code == 200
        assert b'data-testid="task-create-tips"' in resp.data


@pytest.mark.smoke
@pytest.mark.routes
def test_edit_task_page_has_tips(client, app):
    with app.app_context():
        # Minimal data to render page
        user = User(username="ui_editor", role="user")
        user.is_active = True
        project = Project(name="Edit UI Project", client="Client X")
        db.session.add_all([user, project])
        db.session.commit()

        task = Task(project_id=project.id, name="Edit Me", created_by=user.id, assigned_to=user.id)
        db.session.add(task)
        db.session.commit()

        # Login using the login endpoint
        client.post("/login", data={"username": user.username}, follow_redirects=True)

        resp = client.get(f"/tasks/{task.id}/edit")
        assert resp.status_code == 200
        assert b'data-testid="task-edit-tips"' in resp.data


@pytest.mark.smoke
@pytest.mark.routes
def test_kanban_board_aria_and_dnd(authenticated_client, app):
    with app.app_context():
        # Initialize kanban columns first
        from app.models import KanbanColumn

        KanbanColumn.initialize_default_columns()

        # Minimal data for rendering board
        user = User(username="kanban_user", role="admin")
        project = Project(name="Kanban Project", client="Client K", code="KAN")
        db.session.add_all([user, project])
        db.session.commit()

        # authenticated_client already has a logged-in user, but we need to login as the new user
        authenticated_client.post("/login", data={"username": user.username}, follow_redirects=True)

        resp = authenticated_client.get("/kanban")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        # ARIA presence on board wrapper and columns
        assert 'role="application"' in html or 'aria-label="Kanban board"' in html
        assert "aria-live" in html  # counts or empty placeholder live regions


@pytest.mark.smoke
@pytest.mark.routes
def test_kanban_card_shows_project_code_and_no_status_dropdown(authenticated_client, app):
    with app.app_context():
        # Initialize kanban columns first
        from app.models import KanbanColumn

        KanbanColumn.initialize_default_columns()

        admin = User(username="admin_user", role="admin")
        project = Project(name="Very Long Project Name", client="CL", code="VLPN")
        db.session.add_all([admin, project])
        db.session.commit()

        task = Task(project_id=project.id, name="Test Card", created_by=admin.id)
        db.session.add(task)
        db.session.commit()

        # Login as admin using the login endpoint
        authenticated_client.post("/login", data={"username": admin.username}, follow_redirects=True)

        resp = authenticated_client.get("/kanban")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        # Project code badge present
        assert 'data-testid="kanban-project-code"' in html
        assert "VLPN" in html
        # No inline status select in kanban cards
        assert 'class="kanban-status' not in html
