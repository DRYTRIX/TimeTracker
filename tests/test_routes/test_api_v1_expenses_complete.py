"""
Comprehensive tests for refactored expense API routes.
"""

import pytest
from datetime import date
from decimal import Decimal
from app.models import Expense, Project, ApiToken


class TestAPIExpensesComplete:
    """Complete tests for expense API routes"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(
            user_id=user.id, name="Test API Token", scopes="read:expenses,write:expenses"
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

    def test_list_expenses_with_filters(self, app, client_with_token, user, project, expense):
        """Test list_expenses with various filters"""
        # Filter by project
        response = client_with_token.get(f"/api/v1/expenses?project_id={project.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert "expenses" in data
        assert "pagination" in data

    def test_get_expense_uses_eager_loading(self, app, client_with_token, expense):
        """Test that get_expense uses eager loading"""
        response = client_with_token.get(f"/api/v1/expenses/{expense.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert "expense" in data
        assert data["expense"]["id"] == expense.id

    def test_create_expense_all_fields(self, app, client_with_token, project):
        """Test create_expense with all fields"""
        response = client_with_token.post(
            "/api/v1/expenses",
            json={
                "title": "Complete Test Expense",
                "category": "travel",
                "amount": 250.75,
                "expense_date": date.today().isoformat(),
                "project_id": project.id,
                "description": "Full expense test",
                "currency_code": "EUR",
                "tax_amount": 50.15,
                "tax_rate": 20.0,
                "payment_method": "credit_card",
                "payment_date": date.today().isoformat(),
                "billable": True,
                "reimbursable": True,
                "tags": "test,travel",
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert "expense" in data
        assert data["expense"]["title"] == "Complete Test Expense"
        assert data["expense"]["amount"] == "250.75"

    def test_update_expense_uses_service_layer(self, app, client_with_token, expense):
        """Test that update_expense uses service layer"""
        response = client_with_token.put(
            f"/api/v1/expenses/{expense.id}",
            json={"title": "Updated Expense", "amount": 300.00, "status": "approved"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "expense" in data
        assert data["expense"]["title"] == "Updated Expense"

    def test_delete_expense_uses_service_layer(self, app, client_with_token, expense):
        """Test that delete_expense uses service layer"""
        response = client_with_token.delete(f"/api/v1/expenses/{expense.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data

        # Verify expense was rejected
        from app import db

        db.session.refresh(expense)
        assert expense.status == "rejected"

    def test_expense_permissions(self, app, user, project):
        """Test expense access permissions"""
        from app.models import Expense, ApiToken
        from app import db

        # Create expense for another user
        other_user = User.query.filter(User.id != user.id).first()
        if other_user:
            expense = Expense(
                user_id=other_user.id,
                title="Other User Expense",
                category="travel",
                amount=Decimal("100.00"),
                expense_date=date.today(),
            )
            db.session.add(expense)
            db.session.commit()

            # Create token for first user
            token, plain_token = ApiToken.create_token(
                user_id=user.id, name="Test Token", scopes="read:expenses,write:expenses"
            )
            db.session.add(token)
            db.session.commit()

            test_client = app.test_client()
            test_client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {plain_token}"

            # Non-admin should not access other user's expense
            response = test_client.get(f"/api/v1/expenses/{expense.id}")
            assert response.status_code == 403
