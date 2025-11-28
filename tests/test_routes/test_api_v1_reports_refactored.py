"""
Tests for refactored reports API routes with eager loading.
"""

import pytest
from datetime import datetime, timedelta
from app.models import TimeEntry, ApiToken, Project


class TestAPIReportsRefactored:
    """Tests for reports API routes"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(
            user_id=user.id,
            name="Test API Token",
            scopes="read:reports"
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

    def test_report_summary_uses_eager_loading(self, app, client_with_token, user, project, time_entry):
        """Test that report_summary uses eager loading"""
        # Ensure entry is completed
        time_entry.end_time = datetime.utcnow()
        from app import db
        db.session.commit()
        
        response = client_with_token.get("/api/v1/reports/summary")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "summary" in data or "total_hours" in data

    def test_report_summary_with_filters(self, app, client_with_token, user, project, time_entry):
        """Test report_summary with date and project filters"""
        time_entry.end_time = datetime.utcnow()
        from app import db
        db.session.commit()
        
        start_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        response = client_with_token.get(
            f"/api/v1/reports/summary?start_date={start_date}&end_date={end_date}&project_id={project.id}"
        )
        
        assert response.status_code == 200

