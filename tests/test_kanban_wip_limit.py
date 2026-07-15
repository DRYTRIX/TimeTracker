"""Per-column WIP (work-in-progress) limits on kanban columns."""

import pytest

from app import db
from app.models import KanbanColumn

pytestmark = [pytest.mark.integration, pytest.mark.routes]


def test_wip_limit_defaults_to_none(app):
    """A column created without a wip_limit stores NULL (no limit)."""
    with app.app_context():
        column = KanbanColumn(key="wip_none", label="WIP None", project_id=None)
        db.session.add(column)
        db.session.commit()
        stored = KanbanColumn.get_column_by_key("wip_none", project_id=None)
        assert stored.wip_limit is None


def test_wip_limit_roundtrip_and_to_dict(app):
    """A wip_limit value persists and is exposed through to_dict()."""
    with app.app_context():
        column = KanbanColumn(key="wip_three", label="WIP Three", project_id=None, wip_limit=3)
        db.session.add(column)
        db.session.commit()

        stored = KanbanColumn.get_column_by_key("wip_three", project_id=None)
        assert stored.wip_limit == 3
        assert stored.to_dict()["wip_limit"] == 3


def test_create_column_route_persists_wip_limit(app, admin_authenticated_client):
    """POSTing the create form with a wip_limit stores it on the new column."""
    resp = admin_authenticated_client.post(
        "/kanban/columns/create",
        data={"key": "blocked_wip", "label": "Blocked", "wip_limit": "5"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        column = KanbanColumn.get_column_by_key("blocked_wip", project_id=None)
        assert column is not None
        assert column.wip_limit == 5


def test_create_column_route_blank_wip_limit_is_none(app, admin_authenticated_client):
    """A blank wip_limit field results in no limit (NULL)."""
    resp = admin_authenticated_client.post(
        "/kanban/columns/create",
        data={"key": "nolimit_wip", "label": "No Limit", "wip_limit": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        column = KanbanColumn.get_column_by_key("nolimit_wip", project_id=None)
        assert column is not None
        assert column.wip_limit is None


def test_create_column_route_zero_wip_limit_is_none(app, admin_authenticated_client):
    """A zero or negative wip_limit is normalized to no limit (NULL)."""
    resp = admin_authenticated_client.post(
        "/kanban/columns/create",
        data={"key": "zero_wip", "label": "Zero", "wip_limit": "0"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        column = KanbanColumn.get_column_by_key("zero_wip", project_id=None)
        assert column is not None
        assert column.wip_limit is None


def test_edit_column_route_updates_wip_limit(app, admin_authenticated_client):
    """Editing a column can set and later clear its wip_limit."""
    with app.app_context():
        column = KanbanColumn(key="edit_wip", label="Edit WIP", project_id=None)
        db.session.add(column)
        db.session.commit()
        column_id = column.id

    # Set a limit.
    resp = admin_authenticated_client.post(
        f"/kanban/columns/{column_id}/edit",
        data={"label": "Edit WIP", "wip_limit": "7", "is_active": "on"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert KanbanColumn.query.get(column_id).wip_limit == 7

    # Clear the limit.
    resp = admin_authenticated_client.post(
        f"/kanban/columns/{column_id}/edit",
        data={"label": "Edit WIP", "wip_limit": "", "is_active": "on"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert KanbanColumn.query.get(column_id).wip_limit is None
