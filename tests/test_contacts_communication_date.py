"""Regression test for the contact-communication date parsing crash.

The "New Communication" form submits ``communication_date`` / ``follow_up_date``
as single ``<input type="datetime-local">`` values (``YYYY-MM-DDTHH:MM``). The
route previously called ``parse_local_datetime(value)`` with a single argument,
but that helper's signature is ``parse_local_datetime(date_str, time_str)`` — so
every real submission raised ``TypeError: parse_local_datetime() missing 1
required positional argument: 'time_str'`` before a record could be created.

The fix routes both fields through ``parse_local_datetime_from_string`` (which
parses the combined datetime-local string and is None-safe).
"""

import pytest

from app.utils.timezone import parse_local_datetime, parse_local_datetime_from_string


def test_single_arg_parse_local_datetime_still_requires_two_args(app):
    """Guards the root cause: the old single-arg call is a TypeError."""
    with app.app_context():
        with pytest.raises(TypeError):
            parse_local_datetime("2026-07-19T14:30")


def test_from_string_parses_datetime_local_value(app):
    """The datetime-local form value parses to a concrete datetime."""
    with app.app_context():
        parsed = parse_local_datetime_from_string("2026-07-19T14:30")
        assert parsed is not None
        assert parsed.year == 2026 and parsed.month == 7 and parsed.day == 19


@pytest.mark.parametrize("value", ["", "not-a-date", "2026-07-19"])  # no 'T' -> None
def test_from_string_is_none_safe(app, value):
    """Empty/invalid input returns None so the caller's fallback applies."""
    with app.app_context():
        assert parse_local_datetime_from_string(value) is None
