"""
Tests for overtime-as-paid-leave flow (Issue #560).
- Leave type 'overtime' and create_leave_request validation (requested_hours <= YTD).
"""

import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal

from app import db
from app.models import User, TimeEntry, Project, Client
from app.models.time_off import LeaveType, TimeOffRequest
from app.services.workforce_governance_service import WorkforceGovernanceService
from app.utils.overtime import get_overtime_ytd
from factories import UserFactory, ClientFactory, ProjectFactory, TimeEntryFactory


@pytest.fixture
def overtime_leave_type(app):
    """Ensure an overtime leave type exists (code 'overtime')."""
    lt = LeaveType.query.filter_by(code="overtime").first()
    if not lt:
        lt = LeaveType(
            name="Overtime",
            code="overtime",
            is_paid=True,
            annual_allowance_hours=None,
            accrual_hours_per_month=None,
            enabled=True,
        )
        db.session.add(lt)
        db.session.commit()
    return lt


@pytest.fixture
def user_with_ytd_overtime(app, overtime_leave_type):
    """User with 3 hours YTD overtime (one day 11h with 8h standard)."""
    user = UserFactory()
    user.standard_hours_per_day = 8.0
    db.session.add(user)
    client = ClientFactory(name="OT Leave Client")
    db.session.commit()
    project = ProjectFactory(client_id=client.id, name="OT Leave Project")
    db.session.commit()
    today = date.today()
    entry_start = datetime.combine(today, datetime.min.time().replace(hour=9))
    entry_end = entry_start + timedelta(hours=11)
    TimeEntryFactory(
        user_id=user.id,
        project_id=project.id,
        start_time=entry_start,
        end_time=entry_end,
    )
    db.session.commit()
    return user


def test_overtime_leave_request_within_ytd_succeeds(app, user_with_ytd_overtime, overtime_leave_type):
    """Requesting overtime leave with requested_hours <= YTD overtime succeeds."""
    user = user_with_ytd_overtime
    ytd = get_overtime_ytd(user)
    assert ytd["overtime_hours"] >= 3.0, "test user should have at least 3h YTD overtime"
    service = WorkforceGovernanceService()
    start = date.today() + timedelta(days=7)
    end = start + timedelta(days=1)
    result = service.create_leave_request(
        user_id=user.id,
        leave_type_id=overtime_leave_type.id,
        start_date=start,
        end_date=end,
        requested_hours=Decimal("2.5"),
        comment="Take 2.5h as leave",
        submit_now=True,
    )
    assert result["success"] is True
    req = TimeOffRequest.query.filter_by(user_id=user.id, leave_type_id=overtime_leave_type.id).first()
    assert req is not None
    assert float(req.requested_hours) == 2.5


def test_overtime_leave_request_exceeding_ytd_fails(app, user_with_ytd_overtime, overtime_leave_type):
    """Requesting overtime leave with requested_hours > YTD overtime returns error."""
    user = user_with_ytd_overtime
    ytd = get_overtime_ytd(user)
    max_ytd = ytd["overtime_hours"]
    service = WorkforceGovernanceService()
    start = date.today() + timedelta(days=7)
    end = start + timedelta(days=1)
    result = service.create_leave_request(
        user_id=user.id,
        leave_type_id=overtime_leave_type.id,
        start_date=start,
        end_date=end,
        requested_hours=Decimal(str(float(max_ytd) + 10.0)),
        comment="Too many hours",
        submit_now=True,
    )
    assert result["success"] is False
    assert "exceed" in result.get("message", "").lower() or "accumulated" in result.get("message", "").lower()
