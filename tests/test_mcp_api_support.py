"""API support for MCP: agent source, preview, unbilled report, OAuth metadata/DCR."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app import db
from app.constants import TimeEntrySource
from app.models import ApiToken, OAuthApplication, Project, RateOverride, TimeEntry
from app.models.time_entry_approval import ApprovalStatus, TimeEntryApproval
from app.services.invoice_service import InvoiceService

pytestmark = [pytest.mark.api, pytest.mark.integration]


@pytest.fixture
def write_token_client(app, user):
    token, plain = ApiToken.create_token(
        user_id=user.id,
        name="MCP user",
        scopes="read:users,read:projects,read:tasks,read:time_entries,write:time_entries,read:reports",
    )
    db.session.add(token)
    db.session.commit()
    client = app.test_client()
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain}"
    return client


@pytest.fixture
def admin_token_client(app, admin_user):
    token, plain = ApiToken.create_token(
        user_id=admin_user.id,
        name="MCP admin",
        scopes="admin:all,read:users,read:reports,write:time_entries,read:time_entries",
    )
    db.session.add(token)
    db.session.commit()
    client = app.test_client()
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain}"
    return client


def test_time_entry_source_agent_constant():
    assert TimeEntrySource.AGENT.value == "agent"


def test_preview_and_create_duration_entry_with_agent_source(app, write_token_client, user, project):
    day = datetime.utcnow().date().isoformat()
    body = {
        "project_id": project.id,
        "date": day,
        "duration_seconds": 1800,
        "notes": "MCP preview test",
        "source": "agent",
    }
    preview = write_token_client.post("/api/v1/time-entries/preview", json=body)
    assert preview.status_code == 200
    pdata = preview.get_json()
    assert pdata.get("preview") is True
    assert pdata["would_write"]["source"] == "agent"
    assert pdata["would_write"]["start_time"]
    assert pdata["checks"]["ok"] is True

    created = write_token_client.post(
        "/api/v1/time-entries",
        json=body,
        headers={"Idempotency-Key": "mcp-test-agent-1"},
    )
    assert created.status_code == 201
    entry = created.get_json()["time_entry"]
    assert entry["source"] == "agent"
    assert entry["notes"] == "MCP preview test"

    listed = write_token_client.get("/api/v1/time-entries?source=agent")
    assert listed.status_code == 200
    ids = [e["id"] for e in listed.get_json().get("time_entries") or []]
    assert entry["id"] in ids


def test_users_me_includes_mcp_fields(app, write_token_client):
    resp = write_token_client.get("/api/v1/users/me")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "is_admin" in data
    assert "token_scopes" in data
    assert "standard_hours_per_day" in data
    assert "timezone" in data
    assert "read:time_entries" in data["token_scopes"]


def test_oauth_protected_resource_and_dcr(app, user):
    client = app.test_client()
    meta = client.get("/.well-known/oauth-protected-resource")
    assert meta.status_code == 200
    body = meta.get_json()
    assert "resource" in body
    assert "authorization_servers" in body

    as_meta = client.get("/.well-known/oauth-authorization-server")
    assert as_meta.status_code == 200
    assert "registration_endpoint" in as_meta.get_json()

    bad = client.post(
        "/oauth/register",
        json={
            "client_name": "Evil",
            "redirect_uris": ["https://evil.example/cb"],
            "token_endpoint_auth_method": "none",
        },
    )
    assert bad.status_code == 400

    ok = client.post(
        "/oauth/register",
        json={
            "client_name": "Cursor MCP",
            "redirect_uris": ["http://127.0.0.1:8734/callback"],
            "token_endpoint_auth_method": "none",
            "scope_preset": "user",
        },
    )
    assert ok.status_code == 201
    reg = ok.get_json()
    assert reg["client_id"].startswith("tt_app_")
    assert reg["token_endpoint_auth_method"] == "none"
    assert "read:time_entries" in reg["scope"]
    with app.app_context():
        rec = OAuthApplication.query.filter_by(client_id=reg["client_id"]).first()
        assert rec is not None
        assert rec.is_confidential is False


def test_unbilled_report_matches_rate_override(app, admin_token_client, admin_user, project, user):
    with app.app_context():
        proj = Project.query.get(project.id)
        assert proj is not None
        db.session.add(RateOverride(project_id=proj.id, user_id=None, hourly_rate=Decimal("123.00")))
        start = datetime.utcnow() - timedelta(hours=2)
        end = datetime.utcnow() - timedelta(hours=1)
        entry = TimeEntry(
            user_id=admin_user.id,
            project_id=proj.id,
            start_time=start,
            end_time=end,
            duration_seconds=3600,
            billable=True,
            source="agent",
        )
        db.session.add(entry)
        db.session.commit()
        entry_id = entry.id

    resp = admin_token_client.get(f"/api/v1/reports/unbilled?project_id={project.id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_hours"] >= 1.0
    row = next(p for p in data["projects"] if p["project_id"] == project.id)
    assert abs(row["hourly_rate"] - 123.0) < 0.01
    assert abs(row["amount"] - 123.0) < 0.01
    assert entry_id in row["entry_ids"]

    with app.app_context():
        t, plain = ApiToken.create_token(user_id=user.id, name="rpt-user", scopes="read:reports")
        db.session.add(t)
        db.session.commit()
    uc = app.test_client()
    uc.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain}"
    denied = uc.get("/api/v1/reports/unbilled")
    assert denied.status_code == 403


def test_bulk_set_project_and_task_api(app, admin_token_client, user, project, task, test_client):
    from app.models import Project

    with app.app_context():
        other = Project(name="MCP Bulk Target", client_id=test_client.id, description="bulk", billable=True)
        db.session.add(other)
        start = datetime.utcnow() - timedelta(hours=2)
        end = datetime.utcnow() - timedelta(hours=1)
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            task_id=task.id,
            start_time=start,
            end_time=end,
            duration_seconds=3600,
            billable=True,
            source="manual",
        )
        db.session.add(entry)
        db.session.commit()
        entry_id = entry.id
        other_id = other.id

    moved = admin_token_client.post(
        "/api/v1/time-entries/bulk",
        json={"entry_ids": [entry_id], "action": "set_project", "value": other_id},
    )
    assert moved.status_code == 200
    assert moved.get_json()["affected"] == 1

    with app.app_context():
        refreshed = TimeEntry.query.get(entry_id)
        assert refreshed.project_id == other_id
        assert refreshed.task_id is None

    back = admin_token_client.post(
        "/api/v1/time-entries/bulk",
        json={"entry_ids": [entry_id], "action": "set_project", "value": project.id},
    )
    assert back.status_code == 200
    tasked = admin_token_client.post(
        "/api/v1/time-entries/bulk",
        json={"entry_ids": [entry_id], "action": "set_task", "value": task.id},
    )
    assert tasked.status_code == 200
    with app.app_context():
        assert TimeEntry.query.get(entry_id).task_id == task.id


def test_expense_categories_and_reports_api(app, admin_token_client, admin_user, user, project):
    from datetime import date

    from app.models import Expense, ExpenseCategory

    with app.app_context():
        cat = ExpenseCategory.query.filter_by(name="Travel").first()
        if cat is None:
            cat = ExpenseCategory(name="Travel", code="TRV")
            db.session.add(cat)
            db.session.flush()
        expense = Expense(
            user_id=user.id,
            title="Taxi",
            category=cat.name,
            amount=Decimal("25.00"),
            expense_date=date.today(),
            project_id=project.id,
            status="approved",
        )
        db.session.add(expense)
        db.session.commit()

    cats = admin_token_client.get("/api/v1/expense-categories")
    assert cats.status_code == 200
    names = [c["name"] for c in cats.get_json().get("expense_categories") or []]
    assert "Travel" in names

    start = (date.today().replace(day=1)).isoformat()
    end = date.today().isoformat()
    expenses_report = admin_token_client.get(f"/api/v1/reports/expenses?start_date={start}&end_date={end}")
    assert expenses_report.status_code == 200
    edata = expenses_report.get_json()
    assert edata["count"] >= 1
    assert edata["total_amount"] >= 25.0

    missing = admin_token_client.get(f"/api/v1/reports/missing-hours?start_date={start}&end_date={end}")
    assert missing.status_code == 200
    mdata = missing.get_json()
    assert "users" in mdata
    assert mdata["weekdays"] >= 0


def test_admin_can_update_other_users_time_entry(app, admin_token_client, user, project):
    with app.app_context():
        start = datetime.utcnow() - timedelta(hours=2)
        end = datetime.utcnow() - timedelta(hours=1)
        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=start,
            end_time=end,
            duration_seconds=3600,
            billable=True,
            notes="before",
            source="manual",
        )
        db.session.add(entry)
        db.session.commit()
        entry_id = entry.id

    resp = admin_token_client.patch(
        f"/api/v1/time-entries/{entry_id}",
        json={"notes": "admin fixed", "billable": False},
    )
    assert resp.status_code == 200
    body = resp.get_json()["time_entry"]
    assert body["notes"] == "admin fixed"
    assert body["billable"] is False


def test_unbilled_preview_pending_approval_warning(app, admin_user, project):
    with app.app_context():
        start = datetime.utcnow() - timedelta(hours=3)
        end = datetime.utcnow() - timedelta(hours=2)
        entry = TimeEntry(
            user_id=admin_user.id,
            project_id=project.id,
            start_time=start,
            end_time=end,
            duration_seconds=3600,
            billable=True,
            source="agent",
        )
        db.session.add(entry)
        db.session.flush()
        db.session.add(
            TimeEntryApproval(
                time_entry_id=entry.id,
                requested_by=admin_user.id,
                status=ApprovalStatus.PENDING,
                request_comment="MCP unconfirmed",
            )
        )
        db.session.commit()
        proj = Project.query.get(project.id)
        client_id = proj.client_id
        entry_id = entry.id

        preview = InvoiceService().get_client_unbilled_invoice_preview(client_id)
        assert entry_id in (preview.get("pending_approval_entry_ids") or [])
        assert preview.get("warning")
