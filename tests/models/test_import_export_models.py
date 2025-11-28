"""
Model tests for DataImport and DataExport
"""

import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, DataImport, DataExport


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            # Ensure fail-fast production checks are bypassed for tests
            "FLASK_ENV": "testing",
            # Provide a sufficiently strong secret for any residual checks
            "SECRET_KEY": "test-secret-key-do-not-use-in-production-1234567890",
        }
    )

    with app.app_context():
        db.create_all()

        # Create test user
        user = User(username="testuser", role="user")
        db.session.add(user)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


class TestDataImportModel:
    """Test DataImport model"""

    def test_create_import(self, app):
        """Test creating a data import record"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            data_import = DataImport(user_id=user.id, import_type="csv", source_file="test.csv")
            db.session.add(data_import)
            db.session.commit()

            assert data_import.id is not None
            assert data_import.user_id == user.id
            assert data_import.import_type == "csv"
            assert data_import.source_file == "test.csv"
            assert data_import.status == "pending"
            assert data_import.total_records == 0
            assert data_import.successful_records == 0
            assert data_import.failed_records == 0

    def test_import_lifecycle(self, app):
        """Test import record lifecycle"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            # Create import
            data_import = DataImport(user_id=user.id, import_type="toggl", source_file="Toggl Workspace 12345")
            db.session.add(data_import)
            db.session.commit()

            # Start processing
            data_import.start_processing()
            assert data_import.status == "processing"

            # Update progress
            data_import.update_progress(100, 95, 5)
            assert data_import.total_records == 100
            assert data_import.successful_records == 95
            assert data_import.failed_records == 5

            # Partial complete
            data_import.partial_complete()
            assert data_import.status == "partial"
            assert data_import.completed_at is not None

    def test_import_complete(self, app):
        """Test import completion"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            data_import = DataImport(user_id=user.id, import_type="harvest")
            db.session.add(data_import)
            db.session.commit()

            data_import.start_processing()
            data_import.update_progress(50, 50, 0)
            data_import.complete()

            assert data_import.status == "completed"
            assert data_import.completed_at is not None

    def test_import_fail(self, app):
        """Test import failure"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            data_import = DataImport(user_id=user.id, import_type="csv")
            db.session.add(data_import)
            db.session.commit()

            data_import.start_processing()
            data_import.fail("Connection error")

            assert data_import.status == "failed"
            assert data_import.completed_at is not None
            assert data_import.error_log is not None

    def test_import_add_error(self, app):
        """Test adding errors to import"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            data_import = DataImport(user_id=user.id, import_type="csv")
            db.session.add(data_import)
            db.session.commit()

            data_import.add_error("Invalid date format", {"row": 5})
            data_import.add_error("Missing project", {"row": 10})

            import json

            errors = json.loads(data_import.error_log)
            assert len(errors) == 2
            assert errors[0]["error"] == "Invalid date format"

    def test_import_set_summary(self, app):
        """Test setting import summary"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            data_import = DataImport(user_id=user.id, import_type="csv")
            db.session.add(data_import)
            db.session.commit()

            summary = {"total": 100, "successful": 95, "failed": 5, "duration": 30.5}
            data_import.set_summary(summary)

            import json

            stored_summary = json.loads(data_import.import_summary)
            assert stored_summary["total"] == 100
            assert stored_summary["duration"] == 30.5

    def test_import_to_dict(self, app):
        """Test converting import to dictionary"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            data_import = DataImport(user_id=user.id, import_type="csv", source_file="test.csv")
            db.session.add(data_import)
            db.session.commit()

            data_import.update_progress(10, 8, 2)

            import_dict = data_import.to_dict()

            assert import_dict["id"] == data_import.id
            assert import_dict["user"] == "testuser"
            assert import_dict["import_type"] == "csv"
            assert import_dict["total_records"] == 10
            assert import_dict["successful_records"] == 8
            assert import_dict["failed_records"] == 2


class TestDataExportModel:
    """Test DataExport model"""

    def test_create_export(self, app):
        """Test creating a data export record"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            data_export = DataExport(user_id=user.id, export_type="gdpr", export_format="json")
            db.session.add(data_export)
            db.session.commit()

            assert data_export.id is not None
            assert data_export.user_id == user.id
            assert data_export.export_type == "gdpr"
            assert data_export.export_format == "json"
            assert data_export.status == "pending"

    def test_export_lifecycle(self, app):
        """Test export record lifecycle"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            # Create export
            data_export = DataExport(user_id=user.id, export_type="filtered", export_format="csv")
            db.session.add(data_export)
            db.session.commit()

            # Start processing
            data_export.start_processing()
            assert data_export.status == "processing"

            # Complete
            data_export.complete("/tmp/export.csv", 2048, 150)
            assert data_export.status == "completed"
            assert data_export.file_path == "/tmp/export.csv"
            assert data_export.file_size == 2048
            assert data_export.record_count == 150
            assert data_export.completed_at is not None
            assert data_export.expires_at is not None

    def test_export_fail(self, app):
        """Test export failure"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            data_export = DataExport(user_id=user.id, export_type="backup", export_format="json")
            db.session.add(data_export)
            db.session.commit()

            data_export.start_processing()
            data_export.fail("Disk full")

            assert data_export.status == "failed"
            assert data_export.error_message == "Disk full"
            assert data_export.completed_at is not None

    def test_export_with_filters(self, app):
        """Test export with filters"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            filters = {"start_date": "2024-01-01", "end_date": "2024-12-31", "project_id": 5, "billable_only": True}

            data_export = DataExport(user_id=user.id, export_type="filtered", export_format="json", filters=filters)
            db.session.add(data_export)
            db.session.commit()

            import json

            stored_filters = json.loads(data_export.filters)
            assert stored_filters["start_date"] == "2024-01-01"
            assert stored_filters["billable_only"] is True

    def test_export_expiration(self, app):
        """Test export expiration"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            data_export = DataExport(user_id=user.id, export_type="gdpr", export_format="json")
            db.session.add(data_export)
            db.session.commit()

            # Not expired yet
            assert not data_export.is_expired()

            # Complete and check expiration
            data_export.complete("/tmp/test.json", 1024, 100)
            assert not data_export.is_expired()  # Should expire in 7 days

            # Set expiration to past
            data_export.expires_at = datetime.utcnow() - timedelta(days=1)
            db.session.commit()

            assert data_export.is_expired()

    def test_export_to_dict(self, app):
        """Test converting export to dictionary"""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()

            data_export = DataExport(user_id=user.id, export_type="gdpr", export_format="zip")
            db.session.add(data_export)
            db.session.commit()

            data_export.complete("/tmp/export.zip", 4096, 500)

            export_dict = data_export.to_dict()

            assert export_dict["id"] == data_export.id
            assert export_dict["user"] == "testuser"
            assert export_dict["export_type"] == "gdpr"
            assert export_dict["export_format"] == "zip"
            assert export_dict["file_size"] == 4096
            assert export_dict["record_count"] == 500
            assert "expires_at" in export_dict
            assert "is_expired" in export_dict
