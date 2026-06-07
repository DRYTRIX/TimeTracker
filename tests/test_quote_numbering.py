import pytest

from app import db
from app.models import Quote, Settings
from app.utils.invoice_numbering import validate_invoice_pattern


@pytest.mark.unit
def test_validate_quote_pattern_rejects_missing_seq():
    ok, reason = validate_invoice_pattern("{YYYY}-{MM}")
    assert ok is False
    assert "{SEQ}" in reason


@pytest.mark.unit
def test_validate_quote_pattern_rejects_unknown_token():
    ok, reason = validate_invoice_pattern("{YYYY}-{RANDOM}-{SEQ}")
    assert ok is False
    assert "RANDOM" in reason


@pytest.mark.unit
def test_quote_sequence_increments_for_same_pattern(app, user, test_client):
    settings = Settings.get_settings()
    settings.quote_prefix = "OFF"
    settings.quote_number_pattern = "{PREFIX}-{YYYY}-{SEQ}"
    settings.quote_start_number = 5
    db.session.commit()

    quote_number_1 = Quote.generate_quote_number()
    db.session.add(
        Quote(
            quote_number=quote_number_1,
            client_id=test_client.id,
            title="Test quote",
            created_by=user.id,
        )
    )
    db.session.commit()

    quote_number_2 = Quote.generate_quote_number()
    assert quote_number_1.endswith("-005")
    assert quote_number_2.endswith("-006")
