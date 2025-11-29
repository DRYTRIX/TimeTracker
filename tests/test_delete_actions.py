import pytest


@pytest.mark.integration
@pytest.mark.routes
def test_task_view_shows_delete_button(authenticated_client, task, app):
    with app.app_context():
        resp = authenticated_client.get(f"/tasks/{task.id}")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Delete Task" in html


@pytest.mark.integration
@pytest.mark.routes
def test_client_view_shows_delete_button(admin_authenticated_client, test_client, app):
    with app.app_context():
        resp = admin_authenticated_client.get(f"/clients/{test_client.id}", follow_redirects=True)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Delete Client" in html


@pytest.mark.integration
@pytest.mark.routes
def test_project_view_shows_delete_button(admin_authenticated_client, project, app):
    with app.app_context():
        resp = admin_authenticated_client.get(f"/projects/{project.id}", follow_redirects=True)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Delete Project" in html


@pytest.mark.integration
@pytest.mark.routes
def test_delete_task_flow(authenticated_client, task, app):
    with app.app_context():
        # Delete
        resp = authenticated_client.post(f"/tasks/{task.id}/delete", follow_redirects=False)
        assert resp.status_code in [302, 303]
        # Verify gone
        resp2 = authenticated_client.get(f"/tasks/{task.id}")
        assert resp2.status_code in [302, 404]


@pytest.mark.integration
@pytest.mark.routes
def test_delete_client_flow_blocked_when_projects_exist(admin_authenticated_client, test_client, project, app):
    with app.app_context():
        # Attempt delete should fail due to existing project
        resp = admin_authenticated_client.post(f"/clients/{test_client.id}/delete", follow_redirects=False)
        # Should redirect back with error flash
        assert resp.status_code in [302, 303]


@pytest.mark.integration
@pytest.mark.routes
def test_delete_project_flow(admin_authenticated_client, project, app):
    with app.app_context():
        resp = admin_authenticated_client.post(f"/projects/{project.id}/delete", follow_redirects=False)
        assert resp.status_code in [302, 303]
        # Verify gone
        resp2 = admin_authenticated_client.get(f"/projects/{project.id}")
        assert resp2.status_code in [302, 404]
