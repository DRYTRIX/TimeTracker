"""Dashboard today / week / month count whole days in the app timezone.

They counted entries from midnight to "now", so an entry logged for later today was left out of Today's
progress. API v1 changes also clear the dashboard stats cache.
"""

from datetime import date, datetime, timedelta

import pytest

from app import db
from app.models import TimeEntry
from app.models.time_entry import local_now

pytestmark = [pytest.mark.integration]

DAY = date(2026, 11, 16)


def _entry(user, project, start, hours):
    e = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=start,
        end_time=start + timedelta(hours=hours),
        source="manual",
        billable=True,
    )
    db.session.add(e)
    db.session.commit()
    return e


def _day_entries(user, day):
    start = datetime.combine(day, datetime.min.time())
    return (
        TimeEntry.query.filter(
            TimeEntry.user_id == user.id,
            TimeEntry.start_time >= start,
            TimeEntry.start_time < start + timedelta(days=1),
        )
        .order_by(TimeEntry.start_time)
        .all()
    )


# --- what "today" counts ----------------------------------------------------------------------------


def _stats(user):
    from app.services import AnalyticsService

    return AnalyticsService().get_dashboard_stats(user_id=user.id)["time_tracking"]


def test_today_counts_an_entry_that_starts_later_today(app, user, project):
    now = local_now()
    later = now.replace(hour=23, minute=0, second=0, microsecond=0)
    if later <= now:  # running the suite in the last minutes of the day
        pytest.skip("too close to midnight")
    _entry(user, project, later, 0.5)
    assert _stats(user)["today_hours"] == 0.5


def test_today_does_not_count_tomorrow(app, user, project):
    tomorrow = (local_now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    _entry(user, project, tomorrow, 2)
    assert _stats(user)["today_hours"] == 0


def test_live_stats_api_counts_today_by_date(app, authenticated_client, user, project):
    now = local_now()
    later = now.replace(hour=23, minute=0, second=0, microsecond=0)
    if later <= now:
        pytest.skip("too close to midnight")
    _entry(user, project, later, 1)
    _entry(user, project, later + timedelta(days=1), 3)  # tomorrow: not today
    data = authenticated_client.get("/api/dashboard/stats").get_json()
    assert data["today_hours"] == 1


def test_api_v1_create_clears_dashboard_cache(app, user, project):
    from app.models import ApiToken
    from app.utils.cache import get_cache

    token, plain = ApiToken.create_token(user_id=user.id, name="test", scopes="write:time_entries", expires_days=1)
    db.session.add(token)
    db.session.commit()
    cache = get_cache()
    cache.set(f"dashboard:stats:{user.id}", {"stale": True}, ttl=90)
    c = app.test_client()
    resp = c.post(
        "/api/v1/time-entries",
        json={"project_id": project.id, "start_time": "2026-11-16T15:00:00", "end_time": "2026-11-16T16:00:00"},
        headers={"Authorization": f"Bearer {plain}"},
    )
    assert resp.status_code == 201, resp.get_json()
    assert cache.get(f"dashboard:stats:{user.id}") is None
