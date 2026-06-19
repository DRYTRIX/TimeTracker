"""Tests for MetricsService and the analytics dashboard/forecast endpoints.

Covers the profitability + forecasting code added in the analytics dashboard
feature, including the admin-only guard on the org-forecast endpoint.
"""

import pytest

pytestmark = [pytest.mark.integration]

from datetime import date, datetime, timedelta

from app import db
from app.models import TimeEntry
from app.services.metrics_service import MetricsService


# ---------------------------------------------------------------------------
# linear_forecast_with_bands (pure function)
# ---------------------------------------------------------------------------


def test_forecast_empty_series_returns_zeros():
    fc, lo, hi = MetricsService.linear_forecast_with_bands([], forecast_days=5)
    assert fc == [0.0] * 5
    assert lo == [0.0] * 5
    assert hi == [0.0] * 5


def test_forecast_single_value_uses_flat_bands():
    fc, lo, hi = MetricsService.linear_forecast_with_bands([10.0], forecast_days=3)
    assert fc == [10.0] * 3
    assert lo == [pytest.approx(8.5)] * 3
    assert hi == [pytest.approx(11.5)] * 3


def test_forecast_trend_is_increasing_and_bands_ordered():
    fc, lo, hi = MetricsService.linear_forecast_with_bands([1, 2, 3, 4, 5], forecast_days=3)
    assert len(fc) == len(lo) == len(hi) == 3
    # Upward trend should keep climbing past the last observed value (5)
    assert fc[0] > 5
    assert fc[-1] > fc[0]
    # Confidence bands must bracket the central forecast
    for low, mid, high in zip(lo, fc, hi):
        assert low <= mid <= high


def test_forecast_never_returns_negative_values():
    fc, lo, _ = MetricsService.linear_forecast_with_bands([5, 4, 3, 2, 1], forecast_days=10)
    assert all(v >= 0 for v in fc)
    assert all(v >= 0 for v in lo)


# ---------------------------------------------------------------------------
# DB-backed metrics
# ---------------------------------------------------------------------------


def _add_entry(user, project, *, seconds, billable, when):
    entry = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=when,
        end_time=when + timedelta(seconds=seconds),
        billable=billable,
        duration_seconds=seconds,
    )
    db.session.add(entry)
    return entry


def test_profitability_computes_labor_cost_and_margin(app, user, project):
    start = date.today() - timedelta(days=7)
    end = date.today() + timedelta(days=1)
    # 1 billable hour at the project's 75.00/h rate, no revenue booked
    _add_entry(user, project, seconds=3600, billable=True, when=datetime.utcnow() - timedelta(days=1))
    db.session.commit()

    rows = MetricsService().profitability_by_project(start, end, is_admin=True)
    row = next(r for r in rows if r["project_id"] == project.id)
    assert row["labor_cost"] == pytest.approx(75.0)
    assert row["revenue"] == 0.0
    assert row["margin"] == pytest.approx(-75.0)


def test_org_utilization_forecast_ratio_and_shape(app, user, project):
    start = date.today() - timedelta(days=7)
    end = date.today()
    when = datetime.utcnow() - timedelta(days=1)
    _add_entry(user, project, seconds=3600, billable=True, when=when)
    _add_entry(user, project, seconds=3600, billable=False, when=when)
    db.session.commit()

    result = MetricsService().org_utilization_forecast(start, end, forecast_weeks=4)
    assert result["historical_billable_ratio"] == pytest.approx(0.5)
    assert len(result["projected_billable_hours_per_week"]) == 4
    assert all(v >= 0 for v in result["projected_billable_hours_per_week"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def test_profitability_endpoint_returns_projects(authenticated_client):
    r = authenticated_client.get("/api/analytics/profitability?days=30")
    assert r.status_code == 200
    data = r.get_json()
    assert "projects" in data
    assert "start_date" in data and "end_date" in data


def test_profitability_endpoint_rejects_bad_params(authenticated_client):
    r = authenticated_client.get("/api/analytics/profitability?days=notanumber")
    assert r.status_code == 400


def test_hours_forecast_endpoint_returns_data(authenticated_client):
    r = authenticated_client.get("/api/analytics/hours-forecast?days=30&forecast_days=7")
    assert r.status_code == 200


def test_org_forecast_forbidden_for_non_admin(authenticated_client):
    r = authenticated_client.get("/api/analytics/org-forecast")
    assert r.status_code == 403


def test_org_forecast_allowed_for_admin(admin_authenticated_client):
    r = admin_authenticated_client.get("/api/analytics/org-forecast?days=90&forecast_weeks=4")
    assert r.status_code == 200
    data = r.get_json()
    assert "projected_billable_hours_per_week" in data
