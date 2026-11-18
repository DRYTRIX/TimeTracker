"""Tests for support checkout URL helpers and key-source classification."""

from app.config.support_ui import append_query_params, build_support_checkout_urls, build_support_purchase_url
from app.models.donation_interaction import DonationInteraction


def test_append_query_params_merges_system_id():
    url = append_query_params("https://timetracker.drytrix.com/support", {"system_id": "abc-123"})
    assert "system_id=abc-123" in url
    assert url.startswith("https://timetracker.drytrix.com/support")


def test_build_support_purchase_url_with_system_id():
    cfg = {"SUPPORT_PURCHASE_URL": "https://timetracker.drytrix.com/support"}
    url = build_support_purchase_url(cfg, "11111111-2222-3333-4444-555555555555")
    assert url.startswith("https://timetracker.drytrix.com/support?")
    assert "system_id=11111111-2222-3333-4444-555555555555" in url
    assert ".html" not in url


def test_build_support_checkout_urls_license_has_system_id():
    cfg = {"SUPPORT_PURCHASE_URL": "https://example.com/support"}
    urls = build_support_checkout_urls(cfg, "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    assert "system_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" in urls["license"]
    assert urls["license"].startswith("https://example.com/support?")
    # Tips default to Buy Me a Coffee, not the license checkout page
    assert "buymeacoffee.com" in urls["eur5"]
    assert "tip_eur5" in urls["eur5"]
    assert "buymeacoffee.com" in urls["eur10"]
    assert "buymeacoffee.com" in urls["eur25"]
    assert "buymeacoffee.com" in urls["bmc"]


def test_is_key_purchase_source():
    assert DonationInteraction.is_key_purchase_source("donate_page_key") is True
    assert DonationInteraction.is_key_purchase_source("dashboard_widget_key") is True
    assert DonationInteraction.is_key_purchase_source("license_page_key") is True
    assert DonationInteraction.is_key_purchase_source("support_modal_bmc") is False
    assert DonationInteraction.is_key_purchase_source("donate_page_hero") is False
    assert DonationInteraction.is_key_purchase_source(None) is False
