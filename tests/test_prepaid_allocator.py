import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal

from app import db
from app.models import Client, Project, TimeEntry, Invoice, ClientPrepaidConsumption
from factories import InvoiceFactory
from factories import TimeEntryFactory
from app.utils.prepaid_hours import PrepaidHoursAllocator


@pytest.mark.unit
def test_prepaid_allocator_partial_allocation(app, user):
    """Prepaid allocator should consume available hours and bill the remainder."""
    client = Client(
        name="Allocator Client",
        email="allocator@example.com",
        prepaid_hours_monthly=Decimal("5.0"),
        prepaid_reset_day=1,
    )
    db.session.add(client)
    db.session.commit()

    project = Project(name="Allocator Project", client_id=client.id, billable=True, hourly_rate=Decimal("90.00"))
    db.session.add(project)
    db.session.commit()

    invoice = InvoiceFactory(
        invoice_number="INV-ALLOC-001",
        project_id=project.id,
        client_name=client.name,
        client_id=client.id,
        due_date=date.today() + timedelta(days=30),
        created_by=user.id,
        status="draft",
    )
    db.session.add(invoice)
    db.session.commit()

    base_start = datetime(2025, 2, 10, 9, 0, 0)
    hours_blocks = [Decimal("3.0"), Decimal("4.0")]
    entries = []
    for idx, hours in enumerate(hours_blocks):
        start = base_start + timedelta(days=idx)
        end = start + timedelta(hours=float(hours))
        entry = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=start,
            end_time=end,
            billable=True,
            notes=f"Allocation block {idx + 1}",
        )
        entries.append(entry)

    allocator = PrepaidHoursAllocator(client=client, invoice=invoice)
    processed = allocator.process(entries)
    db.session.flush()

    assert len(processed) == 2
    assert processed[0].prepaid_hours == Decimal("3.00")
    assert processed[0].billable_hours == Decimal("0.00")
    assert processed[1].prepaid_hours == Decimal("2.00")
    assert processed[1].billable_hours == Decimal("2.00")
    assert allocator.total_prepaid_hours_assigned == Decimal("5.00")

    consumptions = (
        ClientPrepaidConsumption.query.filter_by(client_id=client.id)
        .order_by(ClientPrepaidConsumption.time_entry_id)
        .all()
    )
    assert len(consumptions) == 2
    assert sum(c.seconds_consumed for c in consumptions) == 5 * 3600

    db.session.refresh(entries[0])
    db.session.refresh(entries[1])
    assert entries[0].billable is False
    assert entries[1].billable is True
