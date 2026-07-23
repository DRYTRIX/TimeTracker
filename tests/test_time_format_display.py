"""
Regression tests for time format preference (Issue #704).

Ensures 24h preference never renders AM/PM via server formatters,
and that time-entry forms expose preference-aware Flatpickr hooks.
"""

from datetime import datetime
from pathlib import Path

import pytest
from flask import url_for

from app import db
from app.models import Settings
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
