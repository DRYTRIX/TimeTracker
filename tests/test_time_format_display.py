"""
Regression tests for time format preference (Issue #704).

Ensures 24h preference never renders AM/PM via server formatters,
and that time-entry forms expose preference-aware Flatpickr hooks.
Also covers follow-ups: compact HHMM typing and edit-page date format.
"""

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from flask import url_for

from app import db
from app.models import Permission, Role, Settings, TimeEntry, User
from app.utils.timezone import (
    format_user_datetime,
    get_resolved_time_format_key,
    get_user_time_format,
)


def test_get_user_time_format_24h_no_ampm(app, user):
    """System + user 24h must use %H:%M (no AM/PM tokens)."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.time_format = "24h"
        db.session.commit()

        user = db.session.merge(user)
        user.time_format = "24h"
        db.session.commit()

        assert get_resolved_time_format_key(user) == "24h"
        assert get_user_time_format(user) == "%H:%M"
        assert "%p" not in get_user_time_format(user)
        assert "%I" not in get_user_time_format(user)


def test_format_user_datetime_24h_never_emits_am_pm(app, user):
    """Formatted datetimes with 24h preference must not contain AM/PM."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.time_format = "24h"
        settings.timezone = "UTC"
        db.session.commit()

        user = db.session.merge(user)
        user.time_format = None  # use system default
        user.timezone = "UTC"
        db.session.commit()

        # Afternoon time that would show PM in 12h mode
        dt = datetime(2026, 7, 23, 16, 59, 0)
        formatted = format_user_datetime(dt, user=user)
        assert "AM" not in formatted.upper()
        assert "PM" not in formatted.upper()
        assert "16:59" in formatted


def test_format_user_datetime_12h_emits_am_pm(app, user):
    """12h preference should still show AM/PM for regression of the opposite path."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.time_format = "12h"
        settings.timezone = "UTC"
        db.session.commit()

        user = db.session.merge(user)
        user.time_format = "12h"
        user.timezone = "UTC"
        db.session.commit()

        dt = datetime(2026, 7, 23, 16, 59, 0)
        formatted = format_user_datetime(dt, user=user)
        assert "PM" in formatted
        assert get_user_time_format(user) == "%I:%M %p"


def test_user_override_beats_system_time_format(app, user):
    """Explicit user 24h wins even when system is 12h."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.time_format = "12h"
        db.session.commit()

        user = db.session.merge(user)
        user.time_format = "24h"
        db.session.commit()

        assert get_resolved_time_format_key(user) == "24h"
        assert get_user_time_format(user) == "%H:%M"


def test_manual_entry_exposes_user_time_input_and_prefs(authenticated_client, user, app):
    """Manual entry page must mark time fields and inject resolved timeFormat."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.time_format = "24h"
        db.session.commit()

        user = db.session.merge(user)
        user.time_format = "24h"
        db.session.commit()

    response = authenticated_client.get(url_for("timer.manual_entry"))
    assert response.status_code == 200
    html = response.data.decode("utf-8")

    assert 'class="form-input user-time-input"' in html or "user-time-input" in html
    assert 'id="start_time"' in html
    assert 'id="end_time"' in html
    assert "timeFormat" in html
    assert '"24h"' in html or "'24h'" in html
    assert "formatUserTime" in html


def test_date_picker_init_uses_24hr_from_prefs():
    """Source helper must treat anything other than 12h as 24-hour Flatpickr mode."""
    src = Path("app/static/date-picker-init.js").read_text(encoding="utf-8")
    assert "user-time-input" in src
    assert "time_24hr" in src
    assert "timeFormat === '12h'" in src
    assert "window.__timePickerUses24hr" in src
    # Wire format must stay 24h HH:MM for form submit
    assert "dateFormat: 'H:i'" in src
    # Compact HHMM parse hook (#704 follow-up)
    assert "window.__parseUserTimeInput" in src
    assert "parseDate: parseTimeDate" in src
    assert "formatDate: formatTimeDate" in src


def _run_parse_user_time_cases():
    """Evaluate __parseUserTimeInput in Node with a minimal DOM stub."""
    js_path = Path("app/static/date-picker-init.js").resolve()
    script = f"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync({json.dumps(str(js_path))}, 'utf8');
const sandbox = {{
  window: {{}},
  document: {{
    readyState: 'complete',
    addEventListener: function () {{}},
    querySelectorAll: function () {{ return []; }},
    body: {{}}
  }},
  MutationObserver: undefined,
  flatpickr: undefined
}};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const p = sandbox.window.__parseUserTimeInput;
if (typeof p !== 'function') {{
  console.error('missing __parseUserTimeInput');
  process.exit(1);
}}
const cases = [
  ['1234', true],
  ['934', true],
  ['12:34', true],
  ['9:05', true],
  ['1:30 PM', false],
  ['130', true],
  ['2560', true],
  ['', true],
];
const out = cases.map(([s, u24]) => p(s, u24));
console.log(JSON.stringify(out));
"""
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"node parse helper failed: {result.stderr or result.stdout}"
        )
    return json.loads(result.stdout.strip())


def test_parse_user_time_input_compact_hhmm():
    """Typing 1234 must become 12:34 (not 12:04); 934 → 09:34 (#704 follow-up)."""
    out = _run_parse_user_time_cases()
    assert out[0] == {"hours": 12, "minutes": 34}
    assert out[1] == {"hours": 9, "minutes": 34}
    assert out[2] == {"hours": 12, "minutes": 34}
    assert out[3] == {"hours": 9, "minutes": 5}
    assert out[4] == {"hours": 13, "minutes": 30}
    assert out[5] == {"hours": 1, "minutes": 30}
    assert out[6] is None  # invalid minutes
    assert out[7] is None


def _ensure_edit_own_permission(user_id):
    perm = Permission.query.filter_by(name="edit_own_time_entries").first()
    if not perm:
        perm = Permission(
            name="edit_own_time_entries",
            description="Edit own time entries",
            category="time_entries",
        )
        db.session.add(perm)
        db.session.flush()
    role = Role.query.filter_by(name="user").first()
    if not role:
        role = Role(name="user", description="User", is_system_role=True)
        db.session.add(role)
        db.session.flush()
    role.add_permission(perm)
    user = User.query.get(user_id)
    if role not in user.roles:
        user.add_role(role)
    db.session.commit()


@pytest.mark.integration
@pytest.mark.routes
def test_edit_timer_uses_user_date_input_and_datetime_filter(
    app, authenticated_client, user, project
):
    """Edit page must use preference-aware date inputs and user_datetime display."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.date_format = "DD.MM.YYYY"
        settings.time_format = "24h"
        settings.timezone = "UTC"
        db.session.commit()

        user = db.session.merge(user)
        user.date_format = "DD.MM.YYYY"
        user.time_format = "24h"
        user.timezone = "UTC"
        db.session.commit()

        _ensure_edit_own_permission(user.id)
        start = datetime(2020, 6, 1, 9, 0, 0)
        end = datetime(2020, 6, 1, 11, 0, 0)
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=start,
            end_time=end,
            source="manual",
        )
        db.session.add(entry)
        db.session.commit()
        eid = entry.id

    response = authenticated_client.get(f"/timer/edit/{eid}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "user-date-input" in html
    assert 'id="start_date"' in html
    assert 'id="end_date"' in html
    # Visible Created summary must not hardcode ISO via strftime in the template output path
    assert "strftime('%Y-%m-%d %H:%M')" not in html

    # Created sidebar uses user_datetime → DD.MM.YYYY (not YYYY-MM-DD)
    created_match = re.search(
        r"Created</span>\s*<span class=\"font-medium\">(.*?)</span>",
        html,
        re.S,
    )
    assert created_match, "Created field missing from edit page"
    created_text = created_match.group(1).strip()
    assert re.search(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", created_text), (
        f"Expected DD.MM.YYYY HH:MM Created, got: {created_text!r}"
    )
    assert re.search(r"\d{4}-\d{2}-\d{2}", created_text) is None


def test_edit_timer_template_uses_user_datetime_filter():
    """Edit timer template must format read-only timestamps with user_datetime."""
    src = Path("app/templates/timer/edit_timer.html").read_text(encoding="utf-8")
    assert "user-date-input" in src
    assert "timer.start_time|user_datetime" in src
    assert "timer.end_time|user_datetime" in src
    assert "timer.created_at|user_datetime" in src
