import io
import os

import pytest

from app.models import ProjectAttachment


@pytest.mark.integration
def test_project_attachment_is_saved_with_the_other_uploads(app, admin_authenticated_client, project):
    response = admin_authenticated_client.post(
        f"/projects/{project.id}/attachments/upload",
        data={"file": (io.BytesIO(b"%PDF-1.4 spec"), "spec.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302

    attachment = ProjectAttachment.query.filter_by(project_id=project.id).one()
    saved = os.path.realpath(os.path.join(app.root_path, "..", attachment.file_path))
    uploads = os.path.realpath(os.path.join(app.root_path, "static", "uploads"))
    try:
        assert saved.startswith(uploads + os.sep)
        assert os.path.exists(saved)
    finally:
        if os.path.exists(saved):
            os.remove(saved)
