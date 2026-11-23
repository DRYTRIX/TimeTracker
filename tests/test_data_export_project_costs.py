"""Regression tests: GDPR export and backup must succeed when project costs exist (#941)."""

import json
import os
import tempfile
from datetime import date
from decimal import Decimal

from app import db
from app.models import DataExport, ProjectCost
from app.utils.data_export import _project_cost_to_dict, create_backup, export_user_data_gdpr


def _create_project_cost(user, project):
    cost = ProjectCost(
        project_id=project.id,
        user_id=user.id,
        description="Hosting fee",
        category="HOSTING",
        amount=Decimal("42.50"),
        cost_date=date(2024, 3, 1),
        notes="Monthly hosting",
        currency_code="EUR",
    )
    db.session.add(cost)
    db.session.commit()
    return cost


def test_project_cost_to_dict_uses_cost_date_and_full_fields(app, user, project):
    cost = _create_project_cost(user, project)
    data = _project_cost_to_dict(cost)

    assert data["cost_date"] == "2024-03-01"
    assert "date" not in data
    assert data["category"] == "HOSTING"
    assert data["currency_code"] == "EUR"
    assert data["invoiced"] is False
    assert data["invoice_id"] is None
    assert data["notes"] == "Monthly hosting"
    assert data["description"] == "Hosting fee"
    assert data["amount"] == 42.5


def test_gdpr_export_succeeds_with_project_cost(app, authenticated_client, user, project):
    upload_dir = tempfile.mkdtemp(prefix="tt_export_")
    app.config["UPLOAD_FOLDER"] = upload_dir

    cost = _create_project_cost(user, project)

    response = authenticated_client.post("/api/export/gdpr", json={"format": "json"})
    assert response.status_code == 200
    result = response.get_json()
    assert result["success"] is True
    assert "export_id" in result

    export_record = DataExport.query.get(result["export_id"])
    assert export_record is not None
    assert export_record.status == "completed"
    assert os.path.isfile(export_record.file_path)

    with open(export_record.file_path, encoding="utf-8") as f:
        payload = json.load(f)

    costs = payload["project_costs"]
    assert len(costs) == 1
    exported = costs[0]
    assert exported["id"] == cost.id
    assert exported["cost_date"] == "2024-03-01"
    assert exported["category"] == "HOSTING"
    assert exported["currency_code"] == "EUR"
    assert exported["invoiced"] is False
    assert exported["invoice_id"] is None
    assert exported["notes"] == "Monthly hosting"


def test_backup_succeeds_with_project_cost(app, admin_authenticated_client, user, project):
    upload_dir = tempfile.mkdtemp(prefix="tt_backup_")
    app.config["UPLOAD_FOLDER"] = upload_dir

    cost = _create_project_cost(user, project)

    response = admin_authenticated_client.post("/api/export/backup")
    assert response.status_code == 200
    result = response.get_json()
    assert result["success"] is True
    assert "export_id" in result

    export_record = DataExport.query.get(result["export_id"])
    assert export_record is not None
    assert export_record.status == "completed"
    assert os.path.isfile(export_record.file_path)

    with open(export_record.file_path, encoding="utf-8") as f:
        payload = json.load(f)

    costs = payload["project_costs"]
    assert any(c["id"] == cost.id and c["cost_date"] == "2024-03-01" for c in costs)
    exported = next(c for c in costs if c["id"] == cost.id)
    assert exported["category"] == "HOSTING"
    assert exported["currency_code"] == "EUR"
    assert exported["notes"] == "Monthly hosting"


def test_export_helpers_directly_with_project_cost(app, user, project, admin_user):
    """Direct util coverage without HTTP (guards against route/module flakiness)."""
    upload_dir = tempfile.mkdtemp(prefix="tt_direct_")
    app.config["UPLOAD_FOLDER"] = upload_dir

    _create_project_cost(user, project)

    gdpr = export_user_data_gdpr(user_id=user.id, export_format="json")
    assert os.path.isfile(gdpr["filepath"])
    with open(gdpr["filepath"], encoding="utf-8") as f:
        gdpr_payload = json.load(f)
    assert len(gdpr_payload["project_costs"]) == 1
    assert gdpr_payload["project_costs"][0]["cost_date"] == "2024-03-01"

    backup = create_backup(user_id=admin_user.id)
    assert os.path.isfile(backup["filepath"])
    with open(backup["filepath"], encoding="utf-8") as f:
        backup_payload = json.load(f)
    assert any(c["cost_date"] == "2024-03-01" for c in backup_payload["project_costs"])
