import os
from zipfile import ZipFile

from app.utils.backup import create_backup, restore_backup


def test_backup_and_restore_keep_receipts_from_upload_folder(app, tmp_path, monkeypatch):
    # The test database is not under Alembic, so skip the migration step of the restore
    monkeypatch.setattr("flask_migrate.upgrade", lambda *args, **kwargs: None)
    upload_folder = tmp_path / "data_uploads"
    receipt = upload_folder / "receipts" / "receipt.pdf"
    receipt.parent.mkdir(parents=True)
    receipt.write_bytes(b"%PDF-1.4 receipt")
    app.config["UPLOAD_FOLDER"] = str(upload_folder)

    with app.app_context():
        archive = create_backup(app)

    with ZipFile(archive) as zf:
        names = zf.namelist()
    assert "data_uploads/receipts/receipt.pdf" in names
    assert not any(name.startswith("data_uploads/backups/") for name in names)

    receipt.unlink()
    with app.app_context():
        ok, message = restore_backup(app, archive)
    assert ok, message
    assert receipt.read_bytes() == b"%PDF-1.4 receipt"
    os.remove(archive)
