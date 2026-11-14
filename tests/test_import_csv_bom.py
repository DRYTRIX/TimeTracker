"""CSV imports accept files saved with a UTF-8 byte order mark (Excel "CSV UTF-8")."""

import io

import pytest

pytestmark = [pytest.mark.integration]

BOM = "﻿".encode("utf-8")


def test_import_time_entries_csv_with_bom(admin_authenticated_client):
    csv_bytes = BOM + (
        b"project_name,client_name,task_name,start_time,end_time,duration_hours,notes,tags,billable\n"
        b"BOM Project,BOM Client,,2024-01-01 09:00:00,2024-01-01 10:00:00,1.0,note,,true\n"
    )
    response = admin_authenticated_client.post(
        "/api/import/csv",
        data={"file": (io.BytesIO(csv_bytes), "entries.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    summary = response.get_json()["summary"]
    assert summary["successful"] == 1
    assert summary["failed"] == 0


def test_import_clients_csv_with_bom(admin_authenticated_client):
    csv_bytes = BOM + b"name,email\nBOM Client Ltd,billing@example.com\n"
    response = admin_authenticated_client.post(
        "/api/import/csv/clients",
        data={"file": (io.BytesIO(csv_bytes), "clients.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    summary = response.get_json()["summary"]
    assert summary["successful"] == 1
    assert summary["failed"] == 0
