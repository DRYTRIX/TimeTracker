"""InvoiceStepOneService: periods, rates for many entries at once, and when a draft's hours are collected again."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, ProjectFactory, TimeEntryFactory, UserFactory

from app import db
from app.models import RateOverride
from app.services.invoice_step_one_service import (
    BillingPeriod,
    InvoiceStepOneService,
    RateTable,
    StepOneError,
    StepOneSelection,
    period_from_dates,
    resolve_period,
)
from app.utils.invoice_time_entry_items import resolve_entry_rate

pytestmark = [pytest.mark.unit]


def test_periods():
    today = date(2026, 1, 14)
    assert resolve_period("last_month", today=today) == BillingPeriod(
        "last_month", date(2025, 12, 1), date(2025, 12, 31)
    )
    assert resolve_period("this_month", today=today) == BillingPeriod("this_month", date(2026, 1, 1), date(2026, 1, 31))
    assert resolve_period("all", today=today) == BillingPeriod("all")
    assert resolve_period("custom", "2026-01-02", "2026-01-05", today=today).end == date(2026, 1, 5)
    assert resolve_period("nonsense", today=today).kind == "last_month"
    with pytest.raises(StepOneError):
        resolve_period("custom", "2026-01-05", "2026-01-02", today=today)
    with pytest.raises(StepOneError):
        resolve_period("custom", "2026-01-05", "", today=today)


def test_issue_date_is_the_last_day_of_the_period():
    today = date(2026, 1, 14)
    assert resolve_period("last_month", today=today).issue_date(today) == date(2025, 12, 31)
    assert resolve_period("this_month", today=today).issue_date(today) == today
    assert resolve_period("all", today=today).issue_date(today) == today
    assert resolve_period("custom", "2026-01-02", "2026-01-05", today=today).issue_date(today) == date(2026, 1, 5)


def test_stored_period_reads_as_last_month_or_custom():
    today = date(2026, 1, 14)
    assert period_from_dates(date(2025, 12, 1), date(2025, 12, 31), today).kind == "last_month"
    assert period_from_dates(date(2025, 12, 2), date(2025, 12, 31), today).kind == "custom"
    assert period_from_dates(None, None, today).kind == "all"


def test_rate_table_gives_the_same_rate_as_each_entry(app):
    client = ClientFactory(default_hourly_rate=Decimal("30.00"))
    with_rate = ProjectFactory(client_id=client.id, hourly_rate=Decimal("40.00"))
    from_client = ProjectFactory(client_id=client.id, hourly_rate=None)
    person, other = UserFactory(), UserFactory()
    db.session.flush()
    db.session.add_all(
        [
            RateOverride(project_id=with_rate.id, user_id=person.id, hourly_rate=Decimal("50"), effective_from=None),
            RateOverride(
                project_id=with_rate.id, user_id=person.id, hourly_rate=Decimal("60"), effective_from=date(2026, 3, 10)
            ),
            RateOverride(
                project_id=with_rate.id,
                user_id=None,
                hourly_rate=Decimal("45"),
                effective_from=date(2026, 3, 1),
                effective_to=date(2026, 3, 5),
            ),
        ]
    )
    db.session.commit()
    entries = []
    for project in (with_rate, from_client):
        for who in (person, other):
            for day in (2, 9, 12):
                start = datetime(2026, 3, day, 9)
                entries.append(
                    TimeEntryFactory(
                        user_id=who.id, project_id=project.id, start_time=start, end_time=start + timedelta(hours=1)
                    )
                )
    db.session.commit()
    table = RateTable([e.project_id for e in entries])
    for entry in entries:
        assert table(entry) == resolve_entry_rate(entry), (entry.project_id, entry.user_id, entry.start_time)


def _selection(client, project_ids, period, layout="task", template=None, client_entries=False):
    return StepOneSelection(
        client=client,
        project_ids=project_ids,
        period=period,
        layout=layout,
        template=template,
        client_entries=client_entries,
    )


def test_hours_changed_only_for_period_projects_layout_or_template(app):
    client = ClientFactory()
    period = BillingPeriod("custom", date(2026, 3, 1), date(2026, 3, 31))
    before = _selection(client, [1, 2], period, "task", "{task}")
    service = InvoiceStepOneService()
    assert not service.hours_changed(before, _selection(client, [2, 1], period, "task", ""))
    assert service.hours_changed(before, _selection(client, [1], period, "task", "{task}"))
    assert service.hours_changed(before, _selection(client, [1, 2], resolve_period("all"), "task", "{task}"))
    assert service.hours_changed(before, _selection(client, [1, 2], period, "person", "{task}"))
    assert service.hours_changed(before, _selection(client, [1, 2], period, "task", "{task} ({date})"))
    assert service.hours_changed(before, _selection(client, [1, 2], period, "task", "{task}", client_entries=True))
    none = _selection(client, [1, 2], period, "none", None)
    assert not service.hours_changed(none, _selection(client, [1, 2], period, "none", "{task}"))
