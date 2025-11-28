"""
Tests for ExportService.
"""

import pytest
from io import BytesIO
import csv
from datetime import datetime
from app.services import ExportService
from app.repositories import TimeEntryRepository, ProjectRepository


class TestExportService:
    """Test cases for ExportService"""

    def test_export_time_entries_csv(self, db_session, sample_project, sample_user, sample_time_entry):
        """Test exporting time entries to CSV"""
        service = ExportService()

        output = service.export_time_entries_csv(user_id=sample_user.id, project_id=sample_project.id)

        assert output is not None
        assert isinstance(output, BytesIO)

        # Read CSV
        output.seek(0)
        reader = csv.reader(output.read().decode("utf-8").splitlines())
        rows = list(reader)

        # Check header
        assert len(rows) > 0
        assert "Date" in rows[0]
        assert "User" in rows[0]
        assert "Project" in rows[0]

    def test_export_projects_csv(self, db_session, sample_project):
        """Test exporting projects to CSV"""
        service = ExportService()

        output = service.export_projects_csv()

        assert output is not None
        assert isinstance(output, BytesIO)

        # Read CSV
        output.seek(0)
        reader = csv.reader(output.read().decode("utf-8").splitlines())
        rows = list(reader)

        # Check header
        assert len(rows) > 0
        assert "Name" in rows[0]
        assert "Client" in rows[0]
        assert "Status" in rows[0]

    def test_export_invoices_csv(self, db_session, sample_invoice):
        """Test exporting invoices to CSV"""
        service = ExportService()

        output = service.export_invoices_csv()

        assert output is not None
        assert isinstance(output, BytesIO)

        # Read CSV
        output.seek(0)
        reader = csv.reader(output.read().decode("utf-8").splitlines())
        rows = list(reader)

        # Check header
        assert len(rows) > 0
        assert "Invoice Number" in rows[0]
        assert "Client" in rows[0]
        assert "Total" in rows[0]
