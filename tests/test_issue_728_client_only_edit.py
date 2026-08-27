"""Issue #728 follow-up: searchable hierarchy, scripts served, template block guard."""

from datetime import datetime
from pathlib import Path
import re

import pytest

from app import db
from app.models import Client, Permission, Role, TimeEntry, User
from app.services.time_tracking_service import TimeTrackingService


ROOT = Path(__file__).resolve().parents[1]


def _ensure_edit_own_permission(user_id):
    perm = Permission.query.filter_by(name="edit_own_time_entries").first()
    if not perm:
        perm = Permission(
            name="edit_own_time_entries",
            description="Edit own time entries",
            category="time_entries",
        )
        db.session.add(perm)
        db.session.flush()
    role = Role.query.filter_by(name="user").first()
    if not role:
        role = Role(name="user", description="User", is_system_role=True)
        db.session.add(role)
        db.session.flush()
    role.add_permission(perm)
    user = User.query.get(user_id)
    if role not in user.roles:
        user.add_role(role)
    db.session.commit()


@pytest.mark.integration
@pytest.mark.routes
def test_edit_client_only_entry_keeps_project_null(app, authenticated_client, user, project):
    """Saving a client-only entry without selecting a project must keep project_id NULL."""
    with app.app_context():
        _ensure_edit_own_permission(user.id)
        client = Client(name="Placeholder Client", email="placeholder@example.com", created_by=user.id)
        client.status = "active"
        db.session.add(client)
        db.session.flush()
        assert project.id is not None
        entry = TimeEntry(
            user_id=user.id,
            client_id=client.id,
            project_id=None,
            start_time=datetime(2026, 8, 12, 9, 0, 0),
            end_time=datetime(2026, 8, 12, 10, 0, 0),
            source="manual",
            notes="client only placeholder",
        )
        db.session.add(entry)
        db.session.commit()
        eid = entry.id
        cid = client.id

    response = authenticated_client.get(f"/timer/edit/{eid}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "No project (client only)" in html
    assert 'data-searchable-select="project"' in html
    assert 'data-searchable-select="task"' in html
    # Scripts must actually be served (extra_js block was previously discarded by base.html)
    assert "searchable-select.js" in html
    assert "inline-create.js" in html
    assert 'value="">selected>' not in html
    assert 'value="" selected>' in html or 'value=""\n selected>' in html or 'value="" selected >' in html

    response = authenticated_client.post(
        f"/timer/edit/{eid}",
        data={
            "client_id": str(cid),
            "project_id": "",
            "task_id": "",
            "start_date": "2026-08-12",
            "start_time": "09:00",
            "end_date": "2026-08-12",
            "end_time": "10:00",
            "notes": "still client only",
            "billable": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        refreshed = TimeEntry.query.get(eid)
        assert refreshed is not None
        assert refreshed.project_id is None
        assert refreshed.client_id == cid


@pytest.mark.integration
@pytest.mark.routes
def test_edit_page_project_options_carry_data_client_id(app, authenticated_client, user, project):
    with app.app_context():
        _ensure_edit_own_permission(user.id)
        client = Client(name="Hierarchy Client", email="hierarchy@example.com", created_by=user.id)
        client.status = "active"
        db.session.add(client)
        db.session.flush()
        entry = TimeEntry(
            user_id=user.id,
            client_id=client.id,
            project_id=None,
            start_time=datetime(2026, 8, 12, 11, 0, 0),
            end_time=datetime(2026, 8, 12, 12, 0, 0),
            source="manual",
            notes="for hierarchy markup",
        )
        db.session.add(entry)
        db.session.commit()
        eid = entry.id
        expected_attr = f'data-client-id="{project.client_id}"'

    response = authenticated_client.get(f"/timer/edit/{eid}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert expected_attr in html
    assert 'data-filter-by="editTimerClient"' in html
    assert 'data-searchable-select="task"' in html


@pytest.mark.integration
@pytest.mark.routes
def test_manual_entry_and_dashboard_emit_data_client_id(app, authenticated_client, project):
    with app.app_context():
        client_id = project.client_id

    manual = authenticated_client.get("/timer/manual")
    assert manual.status_code == 200
    manual_html = manual.get_data(as_text=True)
    assert f'data-client-id="{client_id}"' in manual_html
    assert "searchable-select.js" in manual_html
    assert "inline-create.js" in manual_html
    assert 'data-searchable-select="task"' in manual_html

    dash = authenticated_client.get("/")
    assert dash.status_code == 200
    dash_html = dash.get_data(as_text=True)
    assert f'data-client-id="{client_id}"' in dash_html
    assert 'data-filter-by="startTimerClient"' in dash_html
    assert "inline-create.js" in dash_html


@pytest.mark.integration
@pytest.mark.routes
def test_project_entry_stores_client_id_null_even_when_client_posted(
    app, authenticated_client, user, project
):
    """UI hierarchy may post both fields; storage must keep client_id NULL for project entries."""
    with app.app_context():
        _ensure_edit_own_permission(user.id)
        pid = project.id
        cid = project.client_id
        entry = TimeEntry(
            user_id=user.id,
            project_id=pid,
            client_id=None,
            start_time=datetime(2026, 8, 12, 13, 0, 0),
            end_time=datetime(2026, 8, 12, 14, 0, 0),
            source="manual",
            notes="project based",
        )
        db.session.add(entry)
        db.session.commit()
        eid = entry.id

    response = authenticated_client.post(
        f"/timer/edit/{eid}",
        data={
            "client_id": str(cid),
            "project_id": str(pid),
            "task_id": "",
            "start_date": "2026-08-12",
            "start_time": "13:00",
            "end_date": "2026-08-12",
            "end_time": "14:00",
            "notes": "still project based",
            "billable": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        refreshed = TimeEntry.query.get(eid)
        assert refreshed is not None
        assert refreshed.project_id == pid
        assert refreshed.client_id is None


@pytest.mark.unit
def test_create_manual_entry_project_clears_client(app, user, project):
    with app.app_context():
        service = TimeTrackingService()
        result = service.create_manual_entry(
            user_id=user.id,
            project_id=project.id,
            client_id=project.client_id,  # both posted (UI hierarchy)
            start_time=datetime(2026, 8, 12, 15, 0, 0),
            end_time=datetime(2026, 8, 12, 16, 0, 0),
            notes="hierarchy both fields",
            billable=True,
            skip_entry_requirements=True,
        )
        assert result["success"], result.get("message")
        entry = result["entry"]
        assert entry.project_id == project.id
        assert entry.client_id is None


@pytest.mark.unit
def test_searchable_select_source_present():
    content = (ROOT / "app" / "static" / "searchable-select.js").read_text(encoding="utf-8")
    assert "data-searchable-select" in content
    assert "data-create" in content
    assert "Create task" in content
    assert "data-filter-by" in content
    assert "ttInlineCreate" in content


@pytest.mark.unit
def test_inline_create_unified_source_present():
    content = (ROOT / "app" / "static" / "inline-create.js").read_text(encoding="utf-8")
    assert "ttInlineCreate" in content
    assert "createTaskInlineModal" in content
    assert "showProjectModal" in content or "open: function" in content


@pytest.mark.unit
def test_base_template_defines_extra_js_block():
    base = (ROOT / "app" / "templates" / "base.html").read_text(encoding="utf-8")
    assert "{% block extra_js %}" in base
    assert "{% block scripts_extra %}" in base


@pytest.mark.unit
def test_child_template_blocks_exist_in_base():
    """Every {% block name %} used by templates that extend base.html must exist in base.

    Prevents silent discard of script blocks (the edit_timer extra_js bug).
    """
    base = (ROOT / "app" / "templates" / "base.html").read_text(encoding="utf-8")
    base_blocks = set(re.findall(r"\{%-?\s*block\s+(\w+)", base))

    # Blocks that are intentionally only in nested/layout parents (not base)
    allowed_missing = set()

    child_blocks = set()
    templates_dir = ROOT / "app" / "templates"
    for path in templates_dir.rglob("*.html"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r"\{%-?\s*extends\s+", text):
            continue
        # Only care about script-related blocks that caused the regression
        for name in re.findall(r"\{%-?\s*block\s+(\w+)", text):
            if name in ("extra_js", "scripts_extra", "extra_css", "content", "title"):
                child_blocks.add(name)

    missing = (child_blocks - base_blocks) - allowed_missing
    assert not missing, f"Child templates use blocks missing from base.html: {sorted(missing)}"
    # Explicitly assert the regression that shipped broken
    assert "extra_js" in base_blocks
    assert "scripts_extra" in base_blocks


@pytest.mark.integration
@pytest.mark.routes
def test_manual_entry_project_gated_on_client_and_modal_rate(app, authenticated_client, project):
    """Manual entry follows the client -> project -> task cascade (#728).

    - Project picker is disabled until a client is selected.
    - Inline create-project modal carries a client default rate and a locked
      client display so the project attaches to the chosen client.
    - Client options expose data-default-rate for the JS prefill.
    """
    manual = authenticated_client.get("/timer/manual")
    assert manual.status_code == 200
    html = manual.get_data(as_text=True)

    # Project select disabled without a selected client (JS re-enables it)
    project_select = re.search(r'<select[^>]*id="project_id".*?</select>', html, re.S)
    assert project_select, "project select missing on manual entry"
    assert "disabled" in project_select.group(0)
    assert 'data-filter-by="client_id"' in project_select.group(0)

    # Create-project modal: rate field + locked client display
    assert 'id="inlineProjectRateField"' in html
    assert 'id="inline_project_hourly_rate"' in html
    assert 'id="inlineProjectClientDisplay"' in html
    assert 'id="inline_project_client_id_locked"' in html

    # Client options carry their default rate for the prefill
    assert re.search(r'<option value="\d+" data-default-rate="', html), (
        "client options must expose data-default-rate"
    )
