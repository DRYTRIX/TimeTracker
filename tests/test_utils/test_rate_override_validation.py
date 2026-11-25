"""Unit tests for rate override validation and overlap detection."""

from datetime import date
from decimal import Decimal

import pytest

from app import db
from app.models import RateOverride
from app.utils.rate_override_validation import validate_rate_override_fields

pytestmark = [pytest.mark.unit]


def test_ranges_overlap_open_ended():
    assert RateOverride._ranges_overlap(None, None, date(2024, 1, 1), date(2024, 2, 1))
    assert RateOverride._ranges_overlap(date(2024, 1, 1), None, None, date(2024, 6, 1))
    assert not RateOverride._ranges_overlap(date(2024, 1, 1), date(2024, 3, 31), date(2024, 4, 1), date(2024, 6, 30))


def test_validate_rejects_negative_rate():
    parsed, errors = validate_rate_override_fields(hourly_rate=-1, project_id=1, user_id=None)
    assert parsed is None
    assert "hourly_rate" in errors


def test_validate_rejects_inverted_dates():
    parsed, errors = validate_rate_override_fields(
        hourly_rate=10,
        effective_from="2024-06-01",
        effective_to="2024-01-01",
        project_id=1,
    )
    assert parsed is None
    assert "effective_to" in errors


def test_has_overlapping_window(app, project, user):
    existing = RateOverride(
        project_id=project.id,
        user_id=user.id,
        hourly_rate=Decimal("100"),
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 6, 30),
    )
    db.session.add(existing)
    db.session.commit()

    assert RateOverride.has_overlapping_window(
        project_id=project.id,
        user_id=user.id,
        effective_from=date(2024, 6, 1),
        effective_to=date(2024, 12, 31),
    )
    assert not RateOverride.has_overlapping_window(
        project_id=project.id,
        user_id=user.id,
        effective_from=date(2024, 7, 1),
        effective_to=date(2024, 12, 31),
    )
    assert not RateOverride.has_overlapping_window(
        project_id=project.id,
        user_id=user.id,
        effective_from=date(2024, 6, 1),
        effective_to=date(2024, 12, 31),
        exclude_id=existing.id,
    )


def test_validate_detects_overlap(app, project, user):
    db.session.add(
        RateOverride(
            project_id=project.id,
            user_id=None,
            hourly_rate=Decimal("80"),
            effective_from=None,
            effective_to=None,
        )
    )
    db.session.commit()

    parsed, errors = validate_rate_override_fields(hourly_rate=90, project_id=project.id, user_id=None)
    assert parsed is None
    assert "effective_from" in errors
