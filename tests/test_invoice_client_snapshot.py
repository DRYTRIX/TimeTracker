"""Invoice client snapshot vs live navigation (issue #991)."""

import csv
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from factories import ClientFactory, InvoiceFactory, ProjectFactory, UserFactory

from app import db
from app.services import ExportService, InvoiceService


@pytest.fixture
def rename_setup(app):
    """Draft invoice with a stale client_name snapshot, linked to a live Client."""
    user = UserFactory(username="snap_user", role="admin")
    client = ClientFactory(
        name="Acme [old]",
        email="old@acme.test",
        address="1 Old Street",
    )
    db.session.commit()
    project = ProjectFactory(name="Snap Project", client_id=client.id, billable=True)
    db.session.commit()
    invoice = InvoiceFactory(
        invoice_number="INV-SNAP-001",
        project_id=project.id,
        client_id=client.id,
        client_name="Acme [old]",
        client_email="old@acme.test",
        client_address="1 Old Street",
        due_date=date.today() + timedelta(days=30),
        created_by=user.id,
        tax_rate=Decimal("0"),
    )
    invoice.status = "draft"
    db.session.commit()
    return {"user": user, "client": client, "project": project, "invoice": invoice}


def test_display_client_name_follows_rename(app, rename_setup):
    client = rename_setup["client"]
    invoice = rename_setup["invoice"]

    client.name = "Acme"
    db.session.commit()
    db.session.refresh(invoice)

    assert invoice.client_name == "Acme [old]"
    assert invoice.display_client_name == "Acme"


def test_list_invoices_shows_live_client_name(app, client, rename_setup):
    user = rename_setup["user"]
    cl = rename_setup["client"]
    invoice = rename_setup["invoice"]

    cl.name = "Acme"
    db.session.commit()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True

    resp = client.get("/invoices", headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Acme" in html
    assert "Acme [old]" not in html
    assert invoice.invoice_number in html


def test_search_finds_invoice_by_live_client_name(app, rename_setup):
    cl = rename_setup["client"]
    invoice = rename_setup["invoice"]
    user = rename_setup["user"]

    cl.name = "Acme Renamed Co"
    db.session.commit()

    result = InvoiceService().list_invoices(
        search="Renamed",
        user_id=user.id,
        is_admin=True,
    )
    ids = {inv.id for inv in result["invoices"]}
    assert invoice.id in ids


def test_draft_save_refreshes_snapshot_from_client(app, client, rename_setup):
    user = rename_setup["user"]
    cl = rename_setup["client"]
    invoice = rename_setup["invoice"]

    cl.name = "Acme"
    cl.email = "new@acme.test"
    cl.address = "2 New Avenue"
    db.session.commit()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True

    resp = client.post(
        f"/invoices/{invoice.id}/edit",
        data={
            "client_name": "Acme [old]",  # stale form value must not win
            "client_email": "old@acme.test",
            "client_address": "1 Old Street",
            "due_date": invoice.due_date.strftime("%Y-%m-%d"),
            "tax_rate": "0",
            "notes": "",
            "terms": "",
            "currency_code": invoice.currency_code or "EUR",
            "description[]": [],
            "quantity[]": [],
            "unit_price[]": [],
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    db.session.refresh(invoice)
    assert invoice.client_name == "Acme"
    assert invoice.client_email == "new@acme.test"
    assert invoice.client_address == "2 New Avenue"


def test_leave_draft_freezes_snapshot_then_rename_ignored(app, rename_setup):
    cl = rename_setup["client"]
    invoice = rename_setup["invoice"]
    user = rename_setup["user"]

    cl.name = "Acme At Issue"
    cl.email = "issue@acme.test"
    cl.address = "Issue Street"
    db.session.commit()

    result = InvoiceService().transition_status(invoice, "issued", actor_id=user.id)
    assert result["success"] is True
    db.session.commit()
    db.session.refresh(invoice)

    assert invoice.status == "issued"
    assert invoice.client_name == "Acme At Issue"
    assert invoice.client_email == "issue@acme.test"
    assert invoice.client_address == "Issue Street"

    cl.name = "Acme After Issue"
    cl.email = "after@acme.test"
    cl.address = "After Street"
    db.session.commit()
    db.session.refresh(invoice)

    # Navigation follows live client; document snapshot stays frozen
    assert invoice.display_client_name == "Acme After Issue"
    assert invoice.client_name == "Acme At Issue"
    assert invoice.client_email == "issue@acme.test"
    assert invoice.client_address == "Issue Street"


def test_export_invoices_csv_uses_live_client_name(app, rename_setup):
    cl = rename_setup["client"]
    invoice = rename_setup["invoice"]

    cl.name = "Acme Export"
    db.session.commit()
    # Keep stale snapshot on the row
    assert invoice.client_name == "Acme [old]"

    output = ExportService().export_invoices_csv()
    assert isinstance(output, BytesIO)
    output.seek(0)
    rows = list(csv.reader(output.read().decode("utf-8").splitlines()))
    assert rows[0][1] == "Client"
    matching = [row for row in rows[1:] if row[0] == invoice.invoice_number]
    assert matching
    assert matching[0][1] == "Acme Export"


def test_sync_client_snapshot_noop_when_client_missing(app, rename_setup):
    invoice = rename_setup["invoice"]
    invoice.client_name = "Kept Stale"
    # Simulate deleted client relationship while keeping the snapshot fields.
    invoice.client = None
    invoice.sync_client_snapshot_from_client()
    assert invoice.client_name == "Kept Stale"
