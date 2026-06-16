"""Tests for integration metadata helpers."""

from types import SimpleNamespace

from app.utils.integration_metadata import get_integration_ref, has_integration_ref, set_integration_ref


def test_set_and_get_integration_ref():
    record = SimpleNamespace(integration_metadata=None)
    set_integration_ref(record, "quickbooks", "invoice_id", "QB-123")
    assert get_integration_ref(record, "quickbooks", "invoice_id") == "QB-123"
    assert has_integration_ref(record, "quickbooks", "invoice_id") is True
    assert has_integration_ref(record, "xero", "invoice_id") is False


def test_integration_ref_merges_providers():
    record = SimpleNamespace(integration_metadata=None)
    set_integration_ref(record, "quickbooks", "invoice_id", "1")
    set_integration_ref(record, "xero", "invoice_id", "2")
    assert get_integration_ref(record, "quickbooks", "invoice_id") == "1"
    assert get_integration_ref(record, "xero", "invoice_id") == "2"
