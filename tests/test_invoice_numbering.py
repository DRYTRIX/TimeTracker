from datetime import date

import pytest

from app import db
from app.models import Invoice, Settings
from app.utils.invoice_numbering import validate_invoice_pattern


@pytest.mark.unit
def test_validate_invoice_pattern_rejects_missing_seq():
    ok, reason = validate_invoice_pattern("{YYYY}-{MM}")
    assert ok is False
    assert "{SEQ}" in reason


@pytest.mark.unit
def test_validate_invoice_pattern_rejects_unknown_token():
    ok, reason = validate_invoice_pattern("{YYYY}-{RANDOM}-{SEQ}")
    assert ok is False
    assert "RANDOM" in reason


@pytest.mark.unit
def test_invoice_sequence_increments_for_same_pattern(app, user, project, test_client):
    settings = Settings.get_settings()
    settings.invoice_prefix = "RE"
    settings.invoice_number_pattern = "{PREFIX}-{YYYY}-{SEQ}"
    settings.invoice_start_number = 5
    db.session.commit()

    invoice_number_1 = Invoice.generate_invoice_number()
    db.session.add(
        Invoice(
            invoice_number=invoice_number_1,
            project_id=project.id,
            client_name=test_client.name,
            due_date=date.today(),
            created_by=user.id,
            client_id=test_client.id,
        )
    )
    db.session.commit()

    invoice_number_2 = Invoice.generate_invoice_number()
    assert invoice_number_1.endswith("-005")
    assert invoice_number_2.endswith("-006")
