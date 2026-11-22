"""Web route tests for bulk marking time entries billable / non-billable on /time-entries."""

from datetime import datetime, timedelta

import pytest

from app import db
from app.models import TimeEntry

pytestmark = [pytest.mark.routes, pytest.mark.integration]


def _entry(user_id, project_id, *, billable=True, paid=False, running=False, hours_ago=3):
    start = datetime.utcnow() - timedelta(hours=hours_ago)
    entry = TimeEntry(
        user_id=user_id,
        project_id=project_id,
        start_time=start,
        end_time=None if running else start + timedelta(hours=1),
        source="manual",
        billable=billable,
    )
    entry.paid = paid
    db.session.add(entry)
    db.session.commit()
    return entry.id


def _post(client, ids, billable, **extra):
    data = {"entry_ids[]": [str(i) for i in ids], "set_billable": "true" if billable else "false"}
    data.update(extra)
    return client.post("/time-entries/bulk-billable", data=data, follow_redirects=True)


def _billable(entry_id):
    db.session.expire_all()
    return TimeEntry.query.get(entry_id).billable


def test_bulk_mark_non_billable_then_billable(app, authenticated_client, user, project):
    ids = [_entry(user.id, project.id, hours_ago=h) for h in (3, 5, 7)]

    resp = _post(authenticated_client, ids, False)
    assert resp.status_code == 200
    assert "3 entries marked non-billable" in resp.get_data(as_text=True)
    assert [_billable(i) for i in ids] == [False, False, False]

    resp = _post(authenticated_client, ids, True)
    assert resp.status_code == 200
    assert "3 entries marked billable" in resp.get_data(as_text=True)
    assert [_billable(i) for i in ids] == [True, True, True]


def test_bulk_mark_billable_skips_invoiced_and_running(app, authenticated_client, user, project):
    ids = [_entry(user.id, project.id, hours_ago=h) for h in (3, 5, 7)]
    paid_id = _entry(user.id, project.id, paid=True, hours_ago=9)
    running_id = _entry(user.id, project.id, running=True, hours_ago=1)

    resp = _post(authenticated_client, ids + [paid_id, running_id], False)
    text = resp.get_data(as_text=True)

    assert "3 entries marked non-billable, 2 skipped: 1 already invoiced, 1 timer running" in text
    assert [_billable(i) for i in ids] == [False, False, False]
    assert _billable(paid_id) is True
    assert _billable(running_id) is True


def test_bulk_mark_billable_all_skipped(app, authenticated_client, user, project):
    paid_id = _entry(user.id, project.id, paid=True)

    resp = _post(authenticated_client, [paid_id], False)

    assert "0 entries marked non-billable, 1 skipped: 1 already invoiced" in resp.get_data(as_text=True)
    assert _billable(paid_id) is True


def test_bulk_mark_billable_skips_other_users_entries_for_non_admin(
    app, authenticated_client, user, admin_user, project
):
    own_id = _entry(user.id, project.id)
    other_id = _entry(admin_user.id, project.id, hours_ago=5)

    resp = _post(authenticated_client, [own_id, other_id], False)

    assert "1 entries marked non-billable, 1 skipped: 1 no permission" in resp.get_data(as_text=True)
    assert _billable(own_id) is False
    assert _billable(other_id) is True


def test_bulk_mark_billable_admin_can_change_other_users_entries(
    app, admin_authenticated_client, user, admin_user, project
):
    other_id = _entry(user.id, project.id)

    resp = _post(admin_authenticated_client, [other_id], False)

    assert "1 entries marked non-billable" in resp.get_data(as_text=True)
    assert _billable(other_id) is False


def test_bulk_mark_billable_keeps_list_filters(app, authenticated_client, user, project):
    entry_id = _entry(user.id, project.id)

    resp = authenticated_client.post(
        "/time-entries/bulk-billable",
        data={"entry_ids[]": [str(entry_id)], "set_billable": "false", "billable": "true"},
    )

    assert resp.status_code == 302
    assert "billable=true" in resp.headers["Location"]
    assert _billable(entry_id) is False


def test_bulk_mark_billable_rejects_invalid_status(app, authenticated_client, user, project):
    entry_id = _entry(user.id, project.id)

    resp = authenticated_client.post(
        "/time-entries/bulk-billable", data={"entry_ids[]": [str(entry_id)], "set_billable": "maybe"}
    )

    assert resp.status_code == 302
    assert _billable(entry_id) is True


def test_time_entries_page_shows_bulk_billable_menu_items(app, authenticated_client, user, project):
    _entry(user.id, project.id)

    resp = authenticated_client.get("/time-entries")

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Mark billable" in html
    assert "Mark non-billable" in html
    assert "showBulkBillableDialog(true)" in html
    assert "showBulkBillableDialog(false)" in html
    assert 'id="bulkBillableForm"' in html
