"""
Regression tests for manual entry task dropdown (Issue #675).

The task dropdown depends on inline JS that must declare `form` before the
suggest-break block references it (temporal dead zone).
"""

import pytest
from flask import url_for


@pytest.mark.integration
@pytest.mark.routes
def test_manual_entry_declares_form_before_suggest_break(authenticated_client):
    """Rendered script must bind `form` before suggest-break code uses it."""
    response = authenticated_client.get(url_for("timer.manual_entry"))
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "loadTasks" in html
    assert "suggestBreakBtn" in html

    form_decl = html.find("getElementById('manualEntryForm')")
    suggest_break_use = html.find("if (suggestBreakBtn && breakTimeInput && form)")
    assert form_decl != -1, "manualEntryForm lookup missing from page script"
    assert suggest_break_use != -1, "suggest-break block missing from page script"
    assert form_decl < suggest_break_use, (
        "form must be declared before suggest-break block (Issue #675 TDZ regression)"
    )
