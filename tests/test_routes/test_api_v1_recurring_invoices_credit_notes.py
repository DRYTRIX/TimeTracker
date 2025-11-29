"""
Tests for recurring invoices and credit notes API routes with eager loading.
"""

import pytest
from datetime import date, timedelta
from app.models import RecurringInvoice, CreditNote, Invoice, ApiToken


class TestAPIRecurringInvoicesCreditNotes:
    """Tests for recurring invoices and credit notes routes"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(
            user_id=user.id,
            name="Test API Token",
            scopes="read:recurring_invoices,write:recurring_invoices,read:invoices,write:invoices",
        )
        from app import db

        db.session.add(token)
        db.session.commit()
        return token, plain_token

    @pytest.fixture
    def client_with_token(self, app, api_token):
        """Create a test client with API token"""
        token, plain_token = api_token
        test_client = app.test_client()
        test_client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain_token}"
        return test_client

    def test_list_recurring_invoices_uses_eager_loading(self, app, client_with_token, recurring_invoice):
        """Test that list_recurring_invoices uses eager loading"""
        response = client_with_token.get("/api/v1/recurring-invoices")

        assert response.status_code == 200
        data = response.get_json()
        assert "recurring_invoices" in data
        assert "pagination" in data

    def test_get_recurring_invoice_uses_eager_loading(self, app, client_with_token, recurring_invoice):
        """Test that get_recurring_invoice uses eager loading"""
        response = client_with_token.get(f"/api/v1/recurring-invoices/{recurring_invoice.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "recurring_invoice" in data
        assert data["recurring_invoice"]["id"] == recurring_invoice.id

    def test_list_credit_notes_uses_eager_loading(self, app, client_with_token, invoice):
        """Test that list_credit_notes uses eager loading"""
        from app import db

        credit_note = CreditNote(
            invoice_id=invoice.id, credit_number="CN-TEST-001", amount=100.00, reason="Test credit", created_by=1
        )
        db.session.add(credit_note)
        db.session.commit()

        response = client_with_token.get("/api/v1/credit-notes")

        assert response.status_code == 200
        data = response.get_json()
        assert "credit_notes" in data
        assert "pagination" in data

    def test_get_credit_note_uses_eager_loading(self, app, client_with_token, invoice):
        """Test that get_credit_note uses eager loading"""
        from app import db

        credit_note = CreditNote(
            invoice_id=invoice.id, credit_number="CN-TEST-002", amount=50.00, reason="Test credit", created_by=1
        )
        db.session.add(credit_note)
        db.session.commit()

        response = client_with_token.get(f"/api/v1/credit-notes/{credit_note.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "credit_note" in data
        assert data["credit_note"]["id"] == credit_note.id
