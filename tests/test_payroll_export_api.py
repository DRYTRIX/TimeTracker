"""Template-aware payroll export API and labor-compliance presets."""

from datetime import datetime, timedelta
from io import BytesIO

import pytest

from app import db
from app.models import TimeEntry
from app.models.payroll_export_template import PayrollExportTemplate
from app.services.labor_compliance_service import LaborComplianceService


@pytest.fixture
def payroll_template(app):
    tmpl = PayrollExportTemplate.query.filter_by(name="Generic Payroll").first()
    if not tmpl:
        tmpl = PayrollExportTemplate.ensure_builtin_defaults()
    return tmpl


@pytest.fixture
def payroll_time_entries(app, user, project):
    # Five weekdays × 10h = 50h → overtime vs FLSA 40h and EU WTD 48h
    base = datetime.utcnow().date()
    # Align to Monday of current ISO week so all hours land in one week
    monday = base - timedelta(days=base.weekday())
    entries = []
    for i in range(5):
        day = monday + timedelta(days=i)
        start = datetime.combine(day, datetime.min.time()) + timedelta(hours=9)
        end = start + timedelta(hours=10)
        entries.append(
            TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=start,
                end_time=end,
                notes=f"day {i}",
                source="manual",
                billable=True,
            )
        )
    db.session.add_all(entries)
    db.session.commit()
    return entries


def test_payroll_export_template_aware_csv(client_with_token, payroll_template, payroll_time_entries, user):
    start = (datetime.utcnow() - timedelta(days=7)).date().isoformat()
    end = datetime.utcnow().date().isoformat()
    resp = client_with_token.get(
        f"/api/v1/exports/payroll?start_date={start}&end_date={end}&template_id={payroll_template.id}"
    )
    assert resp.status_code == 200
    assert "text/csv" in (resp.content_type or "")
    body = resp.data.decode("utf-8")
    for col in (payroll_template.columns or PayrollExportTemplate.DEFAULT_COLUMNS)[:5]:
        assert col in body.splitlines()[0]


def test_payroll_export_xlsx(client_with_token, payroll_template, payroll_time_entries):
    pytest.importorskip("openpyxl")
    start = (datetime.utcnow() - timedelta(days=7)).date().isoformat()
    end = datetime.utcnow().date().isoformat()
    resp = client_with_token.get(
        f"/api/v1/exports/payroll?start_date={start}&end_date={end}" f"&template_id={payroll_template.id}&format=xlsx"
    )
    assert resp.status_code == 200
    assert "spreadsheetml" in (resp.content_type or "") or "octet-stream" in (resp.content_type or "")
    assert len(resp.data) > 100
    # openpyxl can open the buffer
    from openpyxl import load_workbook

    wb = load_workbook(BytesIO(resp.data))
    assert wb.active.max_row >= 1


def test_labor_compliance_us_flsa_preset(app, user, payroll_time_entries):
    monday = datetime.utcnow().date() - timedelta(days=datetime.utcnow().date().weekday())
    start = monday
    end = monday + timedelta(days=6)
    rows, meta = LaborComplianceService().export_rows(
        "us-flsa",
        start_date=start,
        end_date=end,
        user_id=user.id,
        weekly_threshold=40.0,
    )
    assert meta["preset_id"] == "us-flsa"
    assert meta["weekly_threshold"] == 40.0
    assert rows
    assert any(float(r["overtime_hours"]) > 0 for r in rows)


def test_labor_compliance_api_eu_wtd(client_with_token, user, payroll_time_entries):
    monday = datetime.utcnow().date() - timedelta(days=datetime.utcnow().date().weekday())
    start = monday.isoformat()
    end = (monday + timedelta(days=6)).isoformat()
    resp = client_with_token.get(
        f"/api/v1/reports/labor-compliance/eu-wtd?start_date={start}&end_date={end}"
        f"&user_id={user.id}&weekly_threshold=48"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["meta"]["preset_id"] == "eu-wtd"
    assert data["meta"]["weekly_threshold"] == 48.0
    assert data["rows"]
    assert any(float(r["overtime_hours"]) > 0 for r in data["rows"])
