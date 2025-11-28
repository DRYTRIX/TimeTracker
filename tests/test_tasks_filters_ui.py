import pytest


@pytest.mark.smoke
def test_task_view_renders_markdown(app, client, task, authenticated_client):
    # Arrange: give the task a markdown description
    from app import db

    task.description = "# Heading\n\n**Bold** and _italic_."
    db.session.commit()

    # Act
    resp = authenticated_client.get(f"/tasks/{task.id}")

    # Assert: the rendered HTML should include tags produced by markdown filter
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "<h1>" in html or "<h2>" in html
    assert "<strong>" in html or "<b>" in html


@pytest.mark.smoke
def test_project_view_renders_markdown(app, client, project, admin_authenticated_client):
    from app import db

    project.description = "Intro with a list:\n\n- item one\n- item two"
    db.session.commit()

    resp = admin_authenticated_client.get(f"/projects/{project.id}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Look for list markup from markdown
    assert "<ul>" in html and "<li>" in html


import pytest


@pytest.mark.unit
@pytest.mark.routes
@pytest.mark.smoke
def test_tasks_filters_collapsible_ui(authenticated_client):
    resp = authenticated_client.get("/tasks")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="toggleFilters"' in html
    assert 'id="filterBody"' in html
    assert 'id="filterToggleIcon"' in html
    # Ensure localStorage key is referenced (persisted visibility)
    assert "taskListFiltersVisible" in html
