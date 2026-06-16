"""Tests for accounting connector sync configuration."""

from app.integrations.sync_config import export_enabled, should_sync_expenses, should_sync_invoices


def test_export_enabled_respects_direction():
    assert export_enabled({"sync_direction": "timetracker_to_quickbooks"}, "quickbooks") is True
    assert export_enabled({"sync_direction": "quickbooks_to_timetracker"}, "quickbooks") is False
    assert export_enabled({"sync_direction": "bidirectional"}, "quickbooks") is True


def test_should_sync_invoices_honors_flags():
    assert should_sync_invoices({"sync_invoices": True}, "incremental") is True
    assert should_sync_invoices({"sync_invoices": False}, "full") is False
    assert should_sync_invoices({"sync_items": ["expenses"]}, "full") is False


def test_should_sync_expenses_honors_flags():
    assert should_sync_expenses({"sync_expenses": True}, "incremental") is True
    assert should_sync_expenses({"sync_expenses": False}, "full") is False
