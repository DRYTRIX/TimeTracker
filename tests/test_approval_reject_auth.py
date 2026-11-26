"""GHSA-7cx3-pj5m-7982: reject() must enforce the same approver checks as approve()."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app import db
from app.models import ApiToken, TimeEntry, User
from app.models.time_entry_approval import ApprovalPolicy, ApprovalStatus, TimeEntryApproval
from app.services.invoice_approval_service import InvoiceApprovalService
from app.services.time_approval_service import TimeApprovalService


@pytest.fixture
def mallory(app):
    existing = User.query.filter_by(username="mallory").first()
    if existing:
        return existing
    u = User(username="mallory", email="mallory@example.com", role="user")
    u.is_active = True
    u.set_password("password123")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def pending_time_approval(app, user, admin_user, project):
    start = datetime.utcnow() - timedelta(hours=3)
    end = datetime.utcnow() - timedelta(hours=2)
    entry = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=start,
        end_time=end,
        source="manual",
        billable=True,
    )
    db.session.add(entry)
    db.session.flush()

    policy = ApprovalPolicy(
        project_id=project.id,
        enabled=True,
        requires_approval=True,
        approver_user_ids=str(admin_user.id),
    )
    db.session.add(policy)

    approval = TimeEntryApproval(
        time_entry_id=entry.id,
        requested_by=user.id,
        status=ApprovalStatus.PENDING,
    )
    db.session.add(approval)
    db.session.commit()
    return approval


@pytest.fixture
def pending_invoice_approval(app, user, admin_user, invoice):
    result = InvoiceApprovalService().request_approval(
        invoice_id=invoice.id,
        requested_by=user.id,
        approvers=[admin_user.id],
    )
    assert result["success"] is True
    return result["approval"]


def test_time_reject_denied_for_non_approver(app, pending_time_approval, mallory):
    service = TimeApprovalService()
    result = service.reject(pending_time_approval.id, mallory.id, "nope")
    assert result["success"] is False
    assert result.get("error") == "unauthorized"

    db.session.refresh(pending_time_approval)
    assert pending_time_approval.status == ApprovalStatus.PENDING


def test_time_reject_allowed_for_designated_approver(app, pending_time_approval, admin_user):
    service = TimeApprovalService()
    result = service.reject(pending_time_approval.id, admin_user.id, "needs fix")
    assert result["success"] is True

    db.session.refresh(pending_time_approval)
    assert pending_time_approval.status == ApprovalStatus.REJECTED
    assert pending_time_approval.approved_by == admin_user.id


def test_invoice_reject_denied_for_non_stage_approver(app, pending_invoice_approval, mallory):
    service = InvoiceApprovalService()
    result = service.reject(pending_invoice_approval.id, mallory.id, "nope")
    assert result["success"] is False
    assert "not authorized" in result["message"].lower()

    db.session.refresh(pending_invoice_approval)
    assert pending_invoice_approval.status == "pending"


def test_invoice_reject_allowed_for_stage_approver(app, pending_invoice_approval, admin_user):
    service = InvoiceApprovalService()
    result = service.reject(pending_invoice_approval.id, admin_user.id, "revise amounts")
    assert result["success"] is True

    db.session.refresh(pending_invoice_approval)
    assert pending_invoice_approval.status == "rejected"
    assert pending_invoice_approval.rejected_by == admin_user.id


def test_web_time_reject_denied_for_non_approver(client, mallory, pending_time_approval, app):
    client.post("/login", data={"username": mallory.username, "password": "password123"}, follow_redirects=True)
    resp = client.post(
        f"/approvals/{pending_time_approval.id}/reject",
        json={"reason": "unauthorized attempt"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    assert body.get("error") == "unauthorized"

    with app.app_context():
        approval = TimeEntryApproval.query.get(pending_time_approval.id)
        assert approval.status == ApprovalStatus.PENDING


def test_web_invoice_view_denied_for_outsider(client, mallory, pending_invoice_approval):
    client.post("/login", data={"username": mallory.username, "password": "password123"}, follow_redirects=True)
    resp = client.get(f"/invoice-approvals/{pending_invoice_approval.id}", follow_redirects=False)
    assert resp.status_code in (302, 403)
    if resp.status_code == 302:
        assert "/invoice-approvals" in (resp.headers.get("Location") or "")


def test_api_request_approval_requires_invoice_access(client, invoice, mallory, app):
    token, plain = ApiToken.create_token(
        user_id=mallory.id, name="Mallory Token", scopes="read:invoices,write:invoices"
    )
    db.session.add(token)
    db.session.commit()

    resp = client.post(
        f"/api/v1/invoices/{invoice.id}/request-approval",
        json={"approver_ids": [mallory.id]},
        headers={"Authorization": f"Bearer {plain}", "Content-Type": "application/json"},
    )
    assert resp.status_code == 403
