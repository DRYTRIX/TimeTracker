"""Tests for invoice validators (UBL well-formed, veraPDF optional)."""
import pytest

from app.utils.invoice_validators import validate_ubl_wellformed


@pytest.mark.unit
def test_validate_ubl_wellformed_accepts_valid_invoice():
    ubl = '<?xml version="1.0"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"><ID>INV-001</ID></Invoice>'
    passed, msgs = validate_ubl_wellformed(ubl)
    assert passed is True
    assert msgs == []


@pytest.mark.unit
def test_validate_ubl_wellformed_rejects_invalid_xml():
    passed, msgs = validate_ubl_wellformed("<bad>")
    assert passed is False
    assert len(msgs) >= 1


@pytest.mark.unit
def test_validate_ubl_wellformed_rejects_non_invoice_root():
    ubl = '<?xml version="1.0"?><NotInvoice xmlns="urn:test"><x/></NotInvoice>'
    passed, msgs = validate_ubl_wellformed(ubl)
    assert passed is False
    assert "Invoice" in msgs[0]
