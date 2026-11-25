"""Cross-field rules of TimeEntryCreateSchema on POST /api/v1/time-entries.

The rules used to be field-level @validates hooks that read kwargs["data"]. Marshmallow 4 passes
only data_key to those hooks, so task_id was always rejected on create and the other rules misfired.
"""

import pytest
from marshmallow import ValidationError

from app.schemas.time_entry_schema import TimeEntryCreateSchema

pytestmark = [pytest.mark.api, pytest.mark.integration]

START = "2026-11-03T09:00:00"
END = "2026-11-03T10:30:00"


def _post(client_with_token, payload):
    return client_with_token.post("/api/v1/time-entries", json=payload)


def test_create_with_project_and_task_sets_task(client_with_token, project, task):
    resp = _post(
        client_with_token, {"project_id": project.id, "task_id": task.id, "start_time": START, "end_time": END}
    )
    assert resp.status_code == 201, resp.get_json()
    entry = resp.get_json()["time_entry"]
    assert entry["task_id"] == task.id
    assert entry["project_id"] == project.id


def test_task_without_project_is_rejected(client_with_token, test_client, task):
    resp = _post(
        client_with_token, {"client_id": test_client.id, "task_id": task.id, "start_time": START, "end_time": END}
    )
    assert resp.status_code == 400
    assert "task_id" in str(resp.get_json())


def test_null_project_with_client_is_accepted(client_with_token, test_client):
    resp = _post(
        client_with_token, {"project_id": None, "client_id": test_client.id, "start_time": START, "end_time": END}
    )
    assert resp.status_code == 201, resp.get_json()
    assert resp.get_json()["time_entry"]["client_id"] == test_client.id


def test_neither_project_nor_client_is_rejected(client_with_token):
    resp = _post(client_with_token, {"start_time": START, "end_time": END})
    assert resp.status_code == 400
    assert "project_id" in str(resp.get_json())


def test_end_before_start_is_rejected(client_with_token, project):
    resp = _post(client_with_token, {"project_id": project.id, "start_time": END, "end_time": START})
    assert resp.status_code == 400
    assert "end_time" in str(resp.get_json())


@pytest.mark.parametrize(
    "payload, error_field",
    [
        ({"project_id": 1, "task_id": 2, "start_time": START, "end_time": END}, None),
        ({"client_id": 1, "start_time": START}, None),
        ({"project_id": None, "client_id": 1, "start_time": START}, None),
        ({"client_id": None, "project_id": 1, "start_time": START}, None),
        ({"client_id": 1, "task_id": 2, "start_time": START}, "task_id"),
        ({"start_time": START}, "project_id"),
        ({"project_id": 1, "start_time": END, "end_time": START}, "end_time"),
        ({"project_id": 1, "start_time": START, "end_time": START}, "end_time"),
    ],
)
def test_schema_rules(payload, error_field):
    schema = TimeEntryCreateSchema()
    if error_field is None:
        schema.load(payload)
        return
    with pytest.raises(ValidationError) as exc:
        schema.load(payload)
    assert error_field in exc.value.messages


def test_schema_does_not_crash_on_mixed_naive_and_aware_times():
    """A naive start and an aware end cannot be compared; the schema leaves that case to the service."""
    TimeEntryCreateSchema().load({"project_id": 1, "start_time": START, "end_time": "2026-11-03T10:30:00Z"})
