"""Rate per time entry, quantity rounding and missing-rate warnings for invoice lines from time."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, ProjectFactory, TimeEntryFactory, UserFactory

from app import db
from app.models import RateOverride, Task
from app.utils.invoice_time_entry_items import build_time_entry_lines, resolve_entry_rate, round_quantity

pytestmark = pytest.mark.unit


def _entry(user, project, start, minutes=60, task=None):
    entry = TimeEntryFactory(
        user_id=user.id,
        project_id=project.id,
        task_id=task.id if task else None,
        start_time=start,
        end_time=start + timedelta(minutes=minutes),
        billable=True,
    )
    db.session.commit()
    return entry


def _task(project, user, name):
    task = Task(name=name, project_id=project.id, status="todo", created_by=user.id)
    db.session.add(task)
    db.session.commit()
    return task


@pytest.fixture
def rated_project(app):
    client = ClientFactory(default_hourly_rate=Decimal("80.00"))
    project = ProjectFactory(client_id=client.id, hourly_rate=Decimal("100.00"))
    user = UserFactory()
    db.session.commit()
    return client, project, user


def test_round_quantity_half_up():
    assert round_quantity(Decimal("20") / Decimal("60")) == Decimal("0.33")
    assert round_quantity(Decimal("0.125")) == Decimal("0.13")
    assert round_quantity(Decimal("1.5")) == Decimal("1.50")


def test_person_override_applies_from_its_start_date(app, rated_project):
    _client, project, user = rated_project
    db.session.add(
        RateOverride(
            project_id=project.id, user_id=user.id, hourly_rate=Decimal("120.00"), effective_from=date(2026, 3, 15)
        )
    )
    db.session.commit()

    before = _entry(user, project, datetime(2026, 3, 10, 9, 0))
    after = _entry(user, project, datetime(2026, 3, 20, 9, 0))

    assert resolve_entry_rate(before).rate == Decimal("100.00")
    assert resolve_entry_rate(after).rate == Decimal("120.00")
    assert resolve_entry_rate(after).found is True


def test_rate_falls_back_from_project_to_client_to_zero(app, rated_project):
    client, project, user = rated_project
    entry = _entry(user, project, datetime(2026, 3, 10, 9, 0))
    assert resolve_entry_rate(entry).rate == Decimal("100.00")

    project.hourly_rate = None
    db.session.commit()
    assert resolve_entry_rate(entry).rate == Decimal("80.00")
    assert resolve_entry_rate(entry).found is True

    client.default_hourly_rate = None
    db.session.commit()
    missing = resolve_entry_rate(entry)
    assert missing.rate == Decimal("0")
    assert missing.found is False


def test_project_override_wins_over_project_rate(app, rated_project):
    _client, project, user = rated_project
    db.session.add(RateOverride(project_id=project.id, user_id=None, hourly_rate=Decimal("90.00")))
    db.session.commit()
    entry = _entry(user, project, datetime(2026, 3, 10, 9, 0))
    assert resolve_entry_rate(entry).rate == Decimal("90.00")


def test_grouped_lines_split_by_rate(app, rated_project):
    _client, project, user = rated_project
    task = _task(project, user, "Design")
    db.session.add(
        RateOverride(
            project_id=project.id, user_id=user.id, hourly_rate=Decimal("120.00"), effective_from=date(2026, 3, 15)
        )
    )
    db.session.commit()
    e1 = _entry(user, project, datetime(2026, 3, 10, 9, 0), minutes=60, task=task)
    e2 = _entry(user, project, datetime(2026, 3, 20, 9, 0), minutes=120, task=task)

    lines = build_time_entry_lines(1, [e1, e2], group=True)

    by_price = {item.unit_price: item for item in lines.items}
    assert set(by_price) == {Decimal("100.00"), Decimal("120.00")}
    assert by_price[Decimal("100.00")].quantity == Decimal("1.00")
    assert by_price[Decimal("100.00")].time_entry_ids == str(e1.id)
    assert by_price[Decimal("120.00")].quantity == Decimal("2.00")
    assert by_price[Decimal("120.00")].time_entry_ids == str(e2.id)
    for item in lines.items:
        assert item.total_amount == item.quantity * item.unit_price
    assert lines.warnings == []


def test_twenty_minutes_at_100_is_33(app, rated_project):
    _client, project, user = rated_project
    entry = _entry(user, project, datetime(2026, 3, 10, 9, 0), minutes=20)

    for group in (True, False):
        (item,) = build_time_entry_lines(1, [entry], group=group).items
        assert item.quantity == Decimal("0.33")
        assert item.total_amount == Decimal("33.00")


def test_missing_rate_bills_at_zero_with_warning(app):
    client = ClientFactory(default_hourly_rate=None)
    project = ProjectFactory(client_id=client.id, hourly_rate=None, name="No Rate Project")
    user = UserFactory(full_name="Dana Example")
    db.session.commit()
    e1 = _entry(user, project, datetime(2026, 3, 10, 9, 0), minutes=90)
    e2 = _entry(user, project, datetime(2026, 3, 11, 9, 0), minutes=30)

    lines = build_time_entry_lines(1, [e1, e2], group=True)

    (item,) = lines.items
    assert item.unit_price == Decimal("0")
    assert item.quantity == Decimal("2.00")
    (missing,) = lines.missing_rates
    assert missing.hours == Decimal("2")
    assert sorted(missing.entry_ids) == sorted([e1.id, e2.id])
    assert lines.warnings == ["2.00 h were added at 0: no hourly rate for No Rate Project / Dana Example"]


def test_project_grouping_keeps_one_line_per_project_and_rate(app, rated_project):
    _client, project, user = rated_project
    task_a = _task(project, user, "Design")
    task_b = _task(project, user, "Build")
    e1 = _entry(user, project, datetime(2026, 3, 10, 9, 0), task=task_a)
    e2 = _entry(user, project, datetime(2026, 3, 11, 9, 0), task=task_b)

    (item,) = build_time_entry_lines(1, [e1, e2], group=True, group_by_task=False, date_format="%Y-%m-%d").items
    assert item.description == f"{project.name} (2026-03-10-2026-03-11)"
    assert item.quantity == Decimal("2.00")
