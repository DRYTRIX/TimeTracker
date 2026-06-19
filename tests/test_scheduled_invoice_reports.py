"""Tests for scheduled invoice report generation."""

import json

import pytest

from app import db
from app.models.reporting import SavedReportView
from app.services.scheduled_report_service import ScheduledReportService
from factories import UserFactory


@pytest.fixture
def invoice_report_view(app):
    with app.app_context():
        user = UserFactory()
        db.session.add(user)
        db.session.commit()

        config = {
            "data_source": "invoices",
            "filters": {},
            "columns": ["invoice_number", "total_amount", "status"],
        }
        view = SavedReportView(
            name="Invoice schedule test",
            owner_id=user.id,
            scope="private",
            config_json=json.dumps(config),
        )
        db.session.add(view)
        db.session.commit()
        yield view, user
        db.session.delete(view)
        db.session.delete(user)
        db.session.commit()


def test_generate_report_data_uses_invoice_data_source(app, invoice_report_view):
    view, user = invoice_report_view
    with app.app_context():
        service = ScheduledReportService()
        config = json.loads(view.config_json)
        data = service._generate_report_data(view, config, user_id=user.id)
        assert data.get("message") != "Invoice reports not yet implemented"
        assert "data" in data
