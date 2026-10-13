"""Unit tests for open-redirect helpers in app.utils.safe_redirect."""

import pytest

from app.utils.safe_redirect import is_safe_next_url, is_safe_referrer, is_safe_relative_url

pytestmark = [pytest.mark.unit, pytest.mark.security]


@pytest.mark.parametrize(
    "url",
    [
        "//evil.com",
        "/\\evil",
        "http://evil.com",
        "",
        None,
        "  ",
        "dashboard",
        "https://evil.com/path",
    ],
)
def test_is_safe_relative_url_rejects_unsafe(url):
    assert is_safe_relative_url(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "/dashboard",
        "/client-portal/foo",
        "/projects/1?tab=times",
        "/settings#profile",
    ],
)
def test_is_safe_relative_url_accepts_relative_paths(url):
    assert is_safe_relative_url(url) is True


def test_is_safe_next_url_with_allowed_prefixes():
    assert is_safe_next_url("/client-portal", allowed_prefixes=("/client-portal",)) is True
    assert is_safe_next_url("/client-portal/invoices", allowed_prefixes=("/client-portal",)) is True
    assert is_safe_next_url("/client-portal?x=1", allowed_prefixes=("/client-portal",)) is True
    assert is_safe_next_url("/dashboard", allowed_prefixes=("/client-portal",)) is False
    assert is_safe_next_url("//evil.com", allowed_prefixes=("/client-portal",)) is False
    # Without prefixes, any safe relative path is OK
    assert is_safe_next_url("/dashboard", allowed_prefixes=None) is True


def test_is_safe_referrer_same_host_vs_other_host(app):
    with app.test_request_context("/", base_url="http://localhost:5000/"):
        assert is_safe_referrer("http://localhost:5000/dashboard") is True
        assert is_safe_referrer("http://localhost:5000/projects/1") is True
        assert is_safe_referrer("/dashboard") is True
        assert is_safe_referrer("http://evil.com/phish") is False
        assert is_safe_referrer("https://evil.com/") is False
        assert is_safe_referrer(None) is False
        assert is_safe_referrer("") is False
        # When same-host is not required, absolute third-party URLs pass
        assert is_safe_referrer("http://evil.com/phish", require_same_host=False) is True


def test_safe_redirect_target_fallback_url(app):
    from app.utils.safe_redirect import safe_redirect_target

    with app.test_request_context("/", base_url="http://localhost:5000/"):
        assert (
            safe_redirect_target(
                "http://evil.com/phish",
                allow_absolute_same_host=True,
                fallback="/invoices/1",
            )
            == "/invoices/1"
        )
        assert (
            safe_redirect_target(
                "http://localhost:5000/projects/1",
                allow_absolute_same_host=True,
                fallback="/invoices/1",
            )
            == "http://localhost:5000/projects/1"
        )


def test_sanitize_log_value_strips_crlf():
    from app.utils.error_handling import sanitize_log_value

    assert "\n" not in sanitize_log_value("a\nb\rc")
    assert sanitize_log_value("a\nb\rc") == "a b c"
    assert len(sanitize_log_value("x" * 1000, max_len=20)) <= 20
