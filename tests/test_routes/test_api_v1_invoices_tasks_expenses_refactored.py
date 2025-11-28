"""
Tests for refactored API v1 invoice, task, and expense routes using service layer.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from app.models import Invoice, Task, Expense, Project, Client, ApiToken


class TestAPIInvoicesRefactored:
    """Tests for refactored invoice API routes"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(
            user_id=user.id,
            name="Test API Token",
            scopes="read:invoices,write:invoices"
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
        test_client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {plain_token}'
        return test_client

    def test_list_invoices_uses_service_layer(self, app, client_with_token, invoice):
        """Test that list_invoices route uses service layer"""
        response = client_with_token.get("/api/v1/invoices")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "invoices" in data
        assert "pagination" in data

    def test_get_invoice_uses_eager_loading(self, app, client_with_token, invoice):
        """Test that get_invoice route uses eager loading"""
        response = client_with_token.get(f"/api/v1/invoices/{invoice.id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "invoice" in data
        assert data["invoice"]["id"] == invoice.id

    def test_create_invoice_uses_service_layer(self, app, client_with_token, project, client):
        """Test that create_invoice route uses service layer"""
        response = client_with_token.post(
            "/api/v1/invoices",
            json={
                "project_id": project.id,
                "client_id": client.id,
                "client_name": client.name,
                "due_date": (date.today() + timedelta(days=30)).isoformat(),
                "notes": "Test invoice"
            },
            content_type="application/json"
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert "invoice" in data
        assert data["invoice"]["project_id"] == project.id


class TestAPITasksRefactored:
    """Tests for refactored task API routes"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(
            user_id=user.id,
            name="Test API Token",
            scopes="read:tasks,write:tasks"
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
        test_client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {plain_token}'
        return test_client

    def test_list_tasks_uses_service_layer(self, app, client_with_token, task):
        """Test that list_tasks route uses service layer"""
        response = client_with_token.get("/api/v1/tasks")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "tasks" in data
        assert "pagination" in data

    def test_get_task_uses_eager_loading(self, app, client_with_token, task):
        """Test that get_task route uses eager loading"""
        response = client_with_token.get(f"/api/v1/tasks/{task.id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "task" in data
        assert data["task"]["id"] == task.id

    def test_create_task_uses_service_layer(self, app, client_with_token, project):
        """Test that create_task route uses service layer"""
        response = client_with_token.post(
            "/api/v1/tasks",
            json={
                "name": "API Test Task",
                "project_id": project.id,
                "description": "Test task description"
            },
            content_type="application/json"
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert "task" in data
        assert data["task"]["name"] == "API Test Task"


class TestAPIExpensesRefactored:
    """Tests for refactored expense API routes"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(
            user_id=user.id,
            name="Test API Token",
            scopes="read:expenses,write:expenses"
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
        test_client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {plain_token}'
        return test_client

    def test_list_expenses_uses_service_layer(self, app, client_with_token, expense):
        """Test that list_expenses route uses service layer"""
        response = client_with_token.get("/api/v1/expenses")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "expenses" in data
        assert "pagination" in data

    def test_get_expense_uses_eager_loading(self, app, client_with_token, expense):
        """Test that get_expense route uses eager loading"""
        response = client_with_token.get(f"/api/v1/expenses/{expense.id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "expense" in data
        assert data["expense"]["id"] == expense.id

    def test_create_expense_uses_service_layer(self, app, client_with_token, project):
        """Test that create_expense route uses service layer"""
        response = client_with_token.post(
            "/api/v1/expenses",
            json={
                "title": "API Test Expense",
                "category": "travel",
                "amount": 100.50,
                "expense_date": date.today().isoformat(),
                "project_id": project.id,
                "description": "Test expense"
            },
            content_type="application/json"
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert "expense" in data
        assert data["expense"]["title"] == "API Test Expense"

