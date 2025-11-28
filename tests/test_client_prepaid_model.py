import pytest
from datetime import datetime, date
from decimal import Decimal

from app import db
from app.models import Client, ClientPrepaidConsumption, User, Project, TimeEntry
from factories import TimeEntryFactory


@pytest.mark.models
def test_client_prepaid_properties_and_consumption(app):
    client = Client(name="Model Client", prepaid_hours_monthly=Decimal("40.0"), prepaid_reset_day=5)
    db.session.add(client)
    db.session.commit()

    assert client.prepaid_plan_enabled is True
    assert client.prepaid_hours_decimal == Decimal("40.00")

    reference = datetime(2025, 3, 7, 12, 0, 0)
    period_start = client.prepaid_month_start(reference)
    assert period_start == date(2025, 3, 5)

    user = User(username="modeluser", email="modeluser@example.com")
    db.session.add(user)
    db.session.commit()

    project = Project(name="Model Project", client_id=client.id, billable=True)
    db.session.add(project)
    db.session.commit()

    entry = TimeEntryFactory(
        user_id=user.id,
        project_id=project.id,
        start_time=datetime(2025, 3, 5, 9, 0, 0),
        end_time=datetime(2025, 3, 5, 21, 0, 0),
        billable=True,
    )

    # Create a consumption record for 12 hours
    consumption = ClientPrepaidConsumption(
        client_id=client.id, time_entry_id=entry.id, allocation_month=period_start, seconds_consumed=12 * 3600
    )
    db.session.add(consumption)
    db.session.commit()

    consumed = client.get_prepaid_consumed_hours(period_start)
    remaining = client.get_prepaid_remaining_hours(period_start)

    assert consumed.quantize(Decimal("0.01")) == Decimal("12.00")
    assert remaining.quantize(Decimal("0.01")) == Decimal("28.00")
