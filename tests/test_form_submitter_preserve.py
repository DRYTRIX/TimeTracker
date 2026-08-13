"""
Regression guards for multi-submit-button forms (#709).

Disabling the clicked submit button during the submit event drops its
name/value from the form entry list. Attendance correction Approve/Reject
and any other dual-button form must preserve the submitter.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"

pytestmark = [pytest.mark.unit]


def test_interactions_preserves_submitter_before_disable():
    content = (STATIC / "interactions.js").read_text(encoding="utf-8")
    assert "preserveSubmitterValue" in content
    assert "e.submitter" in content
    assert 'data-tt-submitter-preserve' in content
    # Must not disable synchronously (would drop submitter from entry list)
    assert "setTimeout(function() {\n            element.disabled = true;" in content or (
        "setTimeout" in content and "element.disabled = true" in content
    )


def test_mobile_submit_buttons_preserve_submitter():
    content = (STATIC / "mobile.js").read_text(encoding="utf-8")
    assert "e.submitter" in content
    assert 'data-tt-submitter-preserve' in content
    assert "setTimeout(() => {\n                        submitter.disabled = true;" in content or (
        "setTimeout" in content and "submitter.disabled = true" in content
    )
