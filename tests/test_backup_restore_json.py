import io
import json


def test_json_backup_restore_is_refused(app, admin_authenticated_client, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    backup = json.dumps({"backup_info": {"version": "1.0"}, "time_entries": []}).encode()

    response = admin_authenticated_client.post(
        "/api/backup/restore",
        data={"file": (io.BytesIO(backup), "backup.json")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "ZIP" in response.get_json()["error"]
