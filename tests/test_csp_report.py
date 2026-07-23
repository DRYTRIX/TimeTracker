"""
Tests for the Content-Security-Policy headers and the violation report endpoint.

The strict, nonce-based policy ships as Content-Security-Policy-Report-Only so that
violations can be observed before it is enforced. Two things have to hold for that to be
worth anything: the browser needs somewhere to send reports, and the policy must not
drown the signal in noise from the ~547 inline event handlers that the enforced policy
permits anyway.
"""

import pytest

pytestmark = [pytest.mark.integration]


class TestCspHeaders:
    def test_enforced_policy_is_present_and_has_no_cdn(self, client):
        response = client.get("/login")
        csp = response.headers.get("Content-Security-Policy", "")

        assert csp, "enforced CSP header missing"
        assert "default-src 'self'" in csp
        for host in ("cdnjs", "jsdelivr", "uicdn", "bunny", "googleapis", "esm.sh"):
            assert host not in csp, f"CSP still allowlists {host}"

    def test_report_only_policy_uses_a_nonce(self, client):
        response = client.get("/login")
        report_only = response.headers.get("Content-Security-Policy-Report-Only", "")

        assert "script-src 'self' 'nonce-" in report_only
        # If it fell back to unsafe-inline the policy would prove nothing.
        assert "script-src 'self' 'unsafe-inline'" not in report_only

    def test_report_only_policy_declares_a_report_uri(self, client):
        """
        Without report-uri the browser has nowhere to send violations — Firefox calls
        such a policy inert: "will not block and cannot report violations".
        """
        response = client.get("/login")
        report_only = response.headers.get("Content-Security-Policy-Report-Only", "")

        assert "report-uri /csp-report" in report_only

    def test_report_only_policy_permits_inline_event_handlers(self, client):
        """
        script-src-attr must be declared explicitly.

        Undeclared, it falls back to script-src, and every one of the ~547 inline
        onclick/onchange/onsubmit handlers violates the policy on every page load. The
        resulting console noise buries the violations that actually matter: <script>
        blocks missing a nonce.
        """
        response = client.get("/login")
        report_only = response.headers.get("Content-Security-Policy-Report-Only", "")

        assert "script-src-attr 'unsafe-inline'" in report_only

    def test_nonce_changes_between_requests(self, client):
        """A nonce that repeats is no better than 'unsafe-inline'."""
        first = client.get("/login").headers.get("Content-Security-Policy-Report-Only", "")
        second = client.get("/login").headers.get("Content-Security-Policy-Report-Only", "")

        assert first and second
        assert first != second, "CSP nonce must be per-request"


class TestCspReportEndpoint:
    def test_accepts_a_violation_report_unauthenticated(self, client):
        """The browser posts these with no session and no CSRF token."""
        payload = {
            "csp-report": {
                "document-uri": "https://example.test/dashboard",
                "violated-directive": "script-src-attr",
                "blocked-uri": "inline",
            }
        }
        response = client.post("/csp-report", json=payload)
        assert response.status_code == 204

    def test_logs_the_violation(self, app, client):
        """
        A handler is attached to app.logger directly rather than using caplog:
        app/utils/setup_logging.py sets `app.logger.propagate = False`, so records never
        reach the root logger that caplog hooks.
        """
        import logging

        captured = []

        class Capture(logging.Handler):
            def emit(self, record):
                captured.append(record.getMessage())

        handler = Capture()
        app.logger.addHandler(handler)
        try:
            client.post(
                "/csp-report",
                json={
                    "csp-report": {
                        "document-uri": "https://example.test/dashboard",
                        "violated-directive": "script-src",
                        "blocked-uri": "https://evil.test/x.js",
                    }
                },
            )
        finally:
            app.logger.removeHandler(handler)

        matches = [m for m in captured if "CSP violation" in m]
        assert matches, f"violation not logged; captured: {captured}"
        assert "script-src" in matches[0]
        assert "https://evil.test/x.js" in matches[0]

    def test_tolerates_malformed_bodies(self, client):
        """A world-writable endpoint must not 500 on junk."""
        assert client.post("/csp-report", data="not json").status_code == 204
        assert client.post("/csp-report", json=[]).status_code == 204
        assert client.post("/csp-report", json={"csp-report": "nope"}).status_code == 204
