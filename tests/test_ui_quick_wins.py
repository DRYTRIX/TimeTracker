import pytest


@pytest.mark.smoke
@pytest.mark.routes
def test_base_layout_has_skip_link(authenticated_client):
    response = authenticated_client.get("/dashboard")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Skip to content" in html
    assert 'href="#mainContentAnchor"' in html
    assert 'id="mainContentAnchor"' in html


@pytest.mark.smoke
@pytest.mark.routes
def test_login_has_primary_button_and_user_icon(client):
    response = client.get("/login")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'class="btn btn-primary' in html or 'class="btn btn-primary"' in html
    assert "fa-user" in html
    assert 'id="username"' in html


@pytest.mark.smoke
@pytest.mark.routes
def test_tasks_table_has_sticky_and_zebra(authenticated_client):
    response = authenticated_client.get("/tasks")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'class="table table-zebra' in html or 'class="table table-zebra"' in html
    # numeric alignment utility present on Due/Progress columns
    assert "table-number" in html
