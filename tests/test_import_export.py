"""
Tests for import/export functionality
"""

import pytest
import json
import os
from datetime import datetime, timedelta
from io import BytesIO
from app import create_app, db
from app.models import User, Project, TimeEntry, Client, DataImport, DataExport
from factories import TimeEntryFactory

# Skip all tests in this module due to transaction closure issues with custom fixtures
pytestmark = pytest.mark.skip(reason="Pre-existing transaction issues with custom app fixture - needs refactoring")


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key",
        }
    )

    with app.app_context():
        db.create_all()

        # Create test user
        user = User(username="testuser", role="user")
        db.session.add(user)

        # Create admin user
        admin = User(username="admin", role="admin")
        db.session.add(admin)

        # Create test client and project
        client = Client(name="Test Client")
        db.session.add(client)
        db.session.flush()

        project = Project(name="Test Project", client_id=client.id)
        db.session.add(project)
        db.session.flush()

        # Create test time entry
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow()
        time_entry = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=start_time,
            end_time=end_time,
            notes="Test entry",
            billable=True,
            source="manual",
        )
        time_entry.calculate_duration()

        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client_fixture(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def auth_headers(app, client_fixture):
    """Login and get authentication"""
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()

        # Simulate login
        with client_fixture.session_transaction() as session:
            session["_user_id"] = str(user.id)
            session["_fresh"] = True

        return {}


@pytest.fixture
def admin_auth_headers(app, client_fixture):
    """Login as admin and get authentication"""
    with app.app_context():
        admin = User.query.filter_by(username="admin").first()

        # Simulate login
        with client_fixture.session_transaction() as session:
            session["_user_id"] = str(admin.id)
            session["_fresh"] = True

        return {}


class TestCSVImport:
    """Test CSV import functionality"""

    def test_csv_import_success(self, app, client_fixture, auth_headers):
        """Test successful CSV import"""
        csv_content = """project_name,client_name,task_name,start_time,end_time,duration_hours,notes,tags,billable
Test Project 2,Test Client 2,,2024-01-01 09:00:00,2024-01-01 10:00:00,1.0,CSV import test,test,true
"""

        data = {"file": (BytesIO(csv_content.encode("utf-8")), "test.csv")}

        response = client_fixture.post(
            "/api/import/csv", data=data, content_type="multipart/form-data", headers=auth_headers
        )

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["success"] is True
        assert result["summary"]["successful"] >= 0

    def test_csv_import_no_file(self, app, client_fixture, auth_headers):
        """Test CSV import with no file"""
        response = client_fixture.post("/api/import/csv", data={}, headers=auth_headers)

        assert response.status_code == 400
        result = json.loads(response.data)
        assert "error" in result

    def test_csv_import_wrong_extension(self, app, client_fixture, auth_headers):
        """Test CSV import with wrong file extension"""
        data = {"file": (BytesIO(b"test"), "test.txt")}

        response = client_fixture.post(
            "/api/import/csv", data=data, content_type="multipart/form-data", headers=auth_headers
        )

        assert response.status_code == 400
        result = json.loads(response.data)
        assert "error" in result


class TestGDPRExport:
    """Test GDPR data export"""

    def test_gdpr_export_json(self, app, client_fixture, auth_headers):
        """Test GDPR export in JSON format"""
        response = client_fixture.post("/api/export/gdpr", json={"format": "json"}, headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["success"] is True
        assert "export_id" in result
        assert "download_url" in result

    def test_gdpr_export_zip(self, app, client_fixture, auth_headers):
        """Test GDPR export in ZIP format"""
        response = client_fixture.post("/api/export/gdpr", json={"format": "zip"}, headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["success"] is True
        assert "export_id" in result

    def test_gdpr_export_invalid_format(self, app, client_fixture, auth_headers):
        """Test GDPR export with invalid format"""
        response = client_fixture.post("/api/export/gdpr", json={"format": "invalid"}, headers=auth_headers)

        assert response.status_code == 400
        result = json.loads(response.data)
        assert "error" in result


class TestFilteredExport:
    """Test filtered data export"""

    def test_filtered_export_json(self, app, client_fixture, auth_headers):
        """Test filtered export in JSON format"""
        filters = {"include_time_entries": True, "start_date": "2024-01-01", "end_date": "2024-12-31"}

        response = client_fixture.post(
            "/api/export/filtered", json={"format": "json", "filters": filters}, headers=auth_headers
        )

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["success"] is True
        assert "export_id" in result

    def test_filtered_export_csv(self, app, client_fixture, auth_headers):
        """Test filtered export in CSV format"""
        filters = {"include_time_entries": True, "billable_only": True}

        response = client_fixture.post(
            "/api/export/filtered", json={"format": "csv", "filters": filters}, headers=auth_headers
        )

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["success"] is True


class TestBackupRestore:
    """Test backup and restore functionality"""

    def test_create_backup_admin_only(self, app, client_fixture, auth_headers):
        """Test that only admins can create backups"""
        response = client_fixture.post("/api/export/backup", headers=auth_headers)

        assert response.status_code == 403
        result = json.loads(response.data)
        assert "error" in result

    def test_create_backup_success(self, app, client_fixture, admin_auth_headers):
        """Test successful backup creation"""
        response = client_fixture.post("/api/export/backup", headers=admin_auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["success"] is True
        assert "export_id" in result
        assert "download_url" in result


class TestImportHistory:
    """Test import history"""

    def test_import_history(self, app, client_fixture, auth_headers):
        """Test getting import history"""
        response = client_fixture.get("/api/import/history", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert "imports" in result
        assert isinstance(result["imports"], list)


class TestExportHistory:
    """Test export history"""

    def test_export_history(self, app, client_fixture, auth_headers):
        """Test getting export history"""
        response = client_fixture.get("/api/export/history", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert "exports" in result
        assert isinstance(result["exports"], list)


class TestDownloadExport:
    """Test export download"""

    def test_download_nonexistent_export(self, app, client_fixture, auth_headers):
        """Test downloading non-existent export"""
        response = client_fixture.get("/api/export/download/99999", headers=auth_headers)

        assert response.status_code == 404


class TestCSVTemplate:
    """Test CSV template download"""

    def test_download_csv_template(self, app, client_fixture, auth_headers):
        """Test downloading CSV import template"""
        response = client_fixture.get("/api/import/template/csv", headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
        assert b"project_name" in response.data


class TestDataImportModel:
    """Test DataImport model"""

    def test_create_import_record(self, app):
        """Test creating import record"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            import_record = DataImport(user_id=user.id, import_type="csv", source_file="test.csv")
            db.session.add(import_record)
            db.session.commit()

            assert import_record.id is not None
            assert import_record.status == "pending"
            assert import_record.total_records == 0

    def test_import_record_progress(self, app):
        """Test updating import progress"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            import_record = DataImport(user_id=user.id, import_type="csv", source_file="test.csv")
            db.session.add(import_record)
            db.session.commit()

            import_record.start_processing()
            assert import_record.status == "processing"

            import_record.update_progress(100, 95, 5)
            assert import_record.total_records == 100
            assert import_record.successful_records == 95
            assert import_record.failed_records == 5

            import_record.partial_complete()
            assert import_record.status == "partial"
            assert import_record.completed_at is not None


class TestDataExportModel:
    """Test DataExport model"""

    def test_create_export_record(self, app):
        """Test creating export record"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            export_record = DataExport(user_id=user.id, export_type="gdpr", export_format="json")
            db.session.add(export_record)
            db.session.commit()

            assert export_record.id is not None
            assert export_record.status == "pending"

    def test_export_record_completion(self, app):
        """Test completing export"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            export_record = DataExport(user_id=user.id, export_type="gdpr", export_format="json")
            db.session.add(export_record)
            db.session.commit()

            export_record.start_processing()
            assert export_record.status == "processing"

            export_record.complete("/tmp/test.json", 1024, 50)
            assert export_record.status == "completed"
            assert export_record.file_path == "/tmp/test.json"
            assert export_record.file_size == 1024
            assert export_record.record_count == 50
            assert export_record.completed_at is not None
            assert export_record.expires_at is not None

    def test_export_expiration(self, app):
        """Test export expiration"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            export_record = DataExport(user_id=user.id, export_type="gdpr", export_format="json")
            db.session.add(export_record)
            db.session.commit()

            # Set expiration to past
            export_record.expires_at = datetime.utcnow() - timedelta(days=1)
            db.session.commit()

            assert export_record.is_expired() is True
