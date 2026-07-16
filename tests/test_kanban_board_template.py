"""Saveable kanban board templates (capture a column layout, re-apply it)."""

import pytest

from app import db
from app.models import KanbanBoardTemplate, KanbanColumn

pytestmark = [pytest.mark.integration, pytest.mark.routes]


def _make_columns(project_id, specs):
    """Create and persist KanbanColumn rows for a scope; return them ordered."""
    for position, spec in enumerate(specs):
        db.session.add(
            KanbanColumn(
                key=spec["key"],
                label=spec.get("label", spec["key"].title()),
                icon=spec.get("icon", "fas fa-circle"),
                color=spec.get("color", "secondary"),
                position=position,
                is_complete_state=spec.get("is_complete_state", False),
                project_id=project_id,
            )
        )
    db.session.commit()
    return KanbanColumn.get_all_columns(project_id=project_id)


def test_spec_from_column_captures_fields(app):
    """spec_from_column snapshots exactly the template spec fields."""
    with app.app_context():
        col = KanbanColumn(
            key="review",
            label="Review",
            icon="fas fa-eye",
            color="warning",
            position=2,
            is_complete_state=False,
            project_id=None,
        )
        spec = KanbanBoardTemplate.spec_from_column(col)
        assert spec == {
            "key": "review",
            "label": "Review",
            "icon": "fas fa-eye",
            "color": "warning",
            "position": 2,
            "is_complete_state": False,
        }


def test_from_columns_and_to_dict(app):
    """from_columns snapshots the ordered columns; to_dict exposes the count."""
    with app.app_context():
        cols = _make_columns(
            project_id=None,
            specs=[
                {"key": "tpl_todo", "label": "To Do"},
                {"key": "tpl_done", "label": "Done", "is_complete_state": True},
            ],
        )
        template = KanbanBoardTemplate.from_columns(
            name="Basic", columns=cols, description="Two columns", created_by=None
        )
        db.session.add(template)
        db.session.commit()

        d = template.to_dict()
        assert d["name"] == "Basic"
        assert d["description"] == "Two columns"
        assert d["column_count"] == 2
        assert [c["key"] for c in d["columns"]] == ["tpl_todo", "tpl_done"]


def test_apply_to_project_creates_columns(app, project):
    """Applying a template to an empty scope creates all its columns."""
    pid = project.id
    with app.app_context():
        template = KanbanBoardTemplate(
            name="Delivery",
            columns=[
                {"key": "a_backlog", "label": "Backlog", "position": 0},
                {
                    "key": "a_done",
                    "label": "Done",
                    "is_complete_state": True,
                    "position": 1,
                },
            ],
        )
        db.session.add(template)
        db.session.commit()

        created = template.apply_to_project(project_id=pid)
        db.session.commit()

        assert created == 2
        cols = KanbanColumn.get_all_columns(project_id=pid)
        assert {c.key for c in cols} == {"a_backlog", "a_done"}
        done = KanbanColumn.get_column_by_key("a_done", project_id=pid)
        assert done.is_complete_state is True
        assert done.is_system is False


def test_apply_to_project_skips_existing_keys(app, project):
    """Without replace, columns whose key already exists are skipped."""
    pid = project.id
    with app.app_context():
        _make_columns(project_id=pid, specs=[{"key": "keep_me", "label": "Keep"}])
        template = KanbanBoardTemplate(
            name="Overlap",
            columns=[
                {"key": "keep_me", "label": "Renamed"},
                {"key": "brand_new", "label": "New"},
            ],
        )
        db.session.add(template)
        db.session.commit()

        created = template.apply_to_project(project_id=pid)
        db.session.commit()

        assert created == 1
        cols = KanbanColumn.get_all_columns(project_id=pid)
        assert {c.key for c in cols} == {"keep_me", "brand_new"}
        # Existing column untouched (label not overwritten).
        assert KanbanColumn.get_column_by_key("keep_me", project_id=pid).label == "Keep"


def test_apply_to_project_replace_wipes_existing(app, project):
    """With replace=True, the scope's existing columns are removed first."""
    pid = project.id
    with app.app_context():
        _make_columns(project_id=pid, specs=[{"key": "old_one", "label": "Old"}])
        template = KanbanBoardTemplate(
            name="Replacement",
            columns=[{"key": "fresh", "label": "Fresh"}],
        )
        db.session.add(template)
        db.session.commit()

        created = template.apply_to_project(project_id=pid, replace=True)
        db.session.commit()

        assert created == 1
        cols = KanbanColumn.get_all_columns(project_id=pid)
        assert {c.key for c in cols} == {"fresh"}


def test_save_template_route_persists(app, admin_authenticated_client, project):
    """POSTing the save form captures the current columns as a template."""
    pid = project.id
    with app.app_context():
        _make_columns(project_id=pid, specs=[{"key": "s_todo"}, {"key": "s_done"}])

    resp = admin_authenticated_client.post(
        "/kanban/templates/save",
        data={
            "name": "Route Template",
            "description": "via route",
            "project_id": str(pid),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        template = KanbanBoardTemplate.query.filter_by(name="Route Template").first()
        assert template is not None
        assert template.column_count == 2
        assert {c["key"] for c in template.columns} == {"s_todo", "s_done"}


def test_save_template_route_requires_name(app, admin_authenticated_client):
    """A blank name does not create a template."""
    resp = admin_authenticated_client.post(
        "/kanban/templates/save",
        data={"name": "", "project_id": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert KanbanBoardTemplate.query.count() == 0


def test_save_template_route_rejects_duplicate_name(app, admin_authenticated_client, project):
    """A case-insensitive duplicate name is rejected."""
    pid = project.id
    with app.app_context():
        _make_columns(project_id=pid, specs=[{"key": "d_todo"}])
        db.session.add(KanbanBoardTemplate(name="Dupe", columns=[{"key": "x"}]))
        db.session.commit()

    resp = admin_authenticated_client.post(
        "/kanban/templates/save",
        data={"name": "dupe", "project_id": str(pid)},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert KanbanBoardTemplate.query.filter(db.func.lower(KanbanBoardTemplate.name) == "dupe").count() == 1


def test_apply_template_route(app, admin_authenticated_client, project):
    """POSTing apply materializes the template's columns into a scope."""
    pid = project.id
    with app.app_context():
        template = KanbanBoardTemplate(
            name="Applier",
            columns=[{"key": "ap_a", "position": 0}, {"key": "ap_b", "position": 1}],
        )
        db.session.add(template)
        db.session.commit()
        template_id = template.id

    resp = admin_authenticated_client.post(
        f"/kanban/templates/{template_id}/apply",
        data={"project_id": str(pid)},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        cols = KanbanColumn.get_all_columns(project_id=pid)
        assert {c.key for c in cols} == {"ap_a", "ap_b"}


def test_delete_template_route(app, admin_authenticated_client):
    """POSTing delete removes the template."""
    with app.app_context():
        template = KanbanBoardTemplate(name="Trash Me", columns=[{"key": "t"}])
        db.session.add(template)
        db.session.commit()
        template_id = template.id

    resp = admin_authenticated_client.post(
        f"/kanban/templates/{template_id}/delete",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert KanbanBoardTemplate.query.get(template_id) is None


def test_list_templates_route_renders(app, admin_authenticated_client):
    """The management page lists saved templates."""
    with app.app_context():
        db.session.add(KanbanBoardTemplate(name="Listed Template", columns=[{"key": "l"}]))
        db.session.commit()

    resp = admin_authenticated_client.get("/kanban/templates")
    assert resp.status_code == 200
    assert b"Listed Template" in resp.data
