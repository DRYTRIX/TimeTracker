import os
import io
import json
import shutil
import tempfile
import subprocess
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
from urllib.parse import urlparse


def get_backup_root_dir(app) -> str:
    """Return the directory where backup archives should be stored.

    Priority:
    1) app.config["BACKUP_FOLDER"] (or env BACKUP_FOLDER / BACKUP_DIR)
    2) <UPLOAD_FOLDER>/backups (UPLOAD_FOLDER defaults to /data/uploads)

    The directory is created if missing.
    """
    # Prefer explicit backup folder if configured
    configured = (
        (app.config.get("BACKUP_FOLDER") if getattr(app, "config", None) else None)
        or os.getenv("BACKUP_FOLDER")
        or os.getenv("BACKUP_DIR")
    )
    if configured:
        backups_dir = os.path.abspath(str(configured))
    else:
        upload_root = (app.config.get("UPLOAD_FOLDER") if getattr(app, "config", None) else None) or os.getenv(
            "UPLOAD_FOLDER", "/data/uploads"
        )
        backups_dir = os.path.abspath(os.path.join(str(upload_root), "backups"))

    # Ensure the directory exists and is writable
    try:
        os.makedirs(backups_dir, exist_ok=True)
    except PermissionError as e:
        raise PermissionError(
            f"Permission denied creating backups directory '{backups_dir}'. "
            "Set BACKUP_FOLDER (or BACKUP_DIR) to a writable path or fix volume permissions."
        ) from e

    if not os.access(backups_dir, os.W_OK):
        raise PermissionError(
            f"Backups directory '{backups_dir}' is not writable. "
            "Set BACKUP_FOLDER (or BACKUP_DIR) to a writable path or fix volume permissions."
        )

    return backups_dir


def _get_backup_root_dir(app):
    """Backward-compatible wrapper for internal callers."""
    return get_backup_root_dir(app)


def _now_timestamp():
    """Return a human-readable local timestamp for file names."""
    # Respect user's preference to use local time across the project
    # rather than UTC for user-facing timestamps.
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _detect_db_type_and_path(app):
    """Detect database type and return a tuple (type, uri, sqlite_path).

    type: 'sqlite' or 'postgresql'
    uri: full SQLAlchemy database URI
    sqlite_path: file path if sqlite, otherwise None
    """
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "") or ""
    if isinstance(uri, str) and uri.startswith("sqlite:///"):
        return "sqlite", uri, uri.replace("sqlite:///", "")
    if isinstance(uri, str) and (uri.startswith("postgresql") or uri.startswith("postgres")):
        return "postgresql", uri, None
    # Default/fallback
    return "unknown", uri, None


def _get_alembic_revision(db_session):
    """Return current alembic revision string or None if unavailable."""
    try:
        from sqlalchemy import text

        result = db_session.execute(text("SELECT version_num FROM alembic_version"))
        row = result.first()
        return row[0] if row else None
    except Exception:
        return None


def _write_manifest(zf, manifest: dict):
    data = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    zf.writestr("manifest.json", data)


def _add_directory_to_zip(zf, source_dir: str, arc_prefix: str):
    if not source_dir or not os.path.isdir(source_dir):
        return
    for root, _, files in os.walk(source_dir):
        for file_name in files:
            abs_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(abs_path, start=source_dir)
            zf.write(abs_path, os.path.join(arc_prefix, rel_path))


def create_backup(app) -> str:
    """Create a comprehensive backup archive and return its absolute path.

    Contents:
    - manifest.json (metadata: created_at, db_type, alembic_revision)
    - db.sqlite (if sqlite) OR db.dump (if postgresql, custom format)
    - settings.json (serialized Settings row for quick inspection)
    - uploads/ (logos and other uploaded assets if present)
    """
    # Late imports to avoid circular dependencies
    from app import db
    from app.models.settings import Settings

    backups_dir = _get_backup_root_dir(app)
    timestamp = _now_timestamp()
    archive_name = f"timetracker_backup_{timestamp}.zip"
    archive_path = os.path.join(backups_dir, archive_name)

    db_type, db_uri, sqlite_path = _detect_db_type_and_path(app)

    # Prepare temporary directory for DB dumps if needed
    tmp_dir = tempfile.mkdtemp(prefix="tt_backup_")
    tmp_db_artifact = None

    try:
        # Create DB artifact
        if db_type == "sqlite" and sqlite_path and os.path.exists(sqlite_path):
            tmp_db_artifact = os.path.join(tmp_dir, "db.sqlite")
            shutil.copy2(sqlite_path, tmp_db_artifact)
        elif db_type == "postgresql":
            # Use parsed connection parameters (avoid SQLAlchemy driver suffix in URI)
            database_url = os.getenv("DATABASE_URL", db_uri)
            parsed = urlparse(database_url) if database_url else None
            host = parsed.hostname if parsed and parsed.hostname else os.getenv("POSTGRES_HOST", "db")
            port = parsed.port if parsed and parsed.port else int(os.getenv("POSTGRES_PORT", "5432"))
            user = parsed.username if parsed and parsed.username else os.getenv("POSTGRES_USER", "timetracker")
            password = parsed.password if parsed and parsed.password else os.getenv("POSTGRES_PASSWORD", "timetracker")
            dbname = parsed.path.lstrip("/") if parsed and parsed.path else os.getenv("POSTGRES_DB", "timetracker")

            tmp_db_artifact = os.path.join(tmp_dir, "db.dump")
            pg_dump_cmd = [
                "pg_dump",
                "--format=custom",
                "-h",
                host,
                "-p",
                str(port),
                "-U",
                user,
                "-d",
                dbname,
                f"--file={tmp_db_artifact}",
            ]
            env = os.environ.copy()
            if password:
                env["PGPASSWORD"] = str(password)
            try:
                completed = subprocess.run(
                    pg_dump_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
                )
            except FileNotFoundError:
                raise RuntimeError("pg_dump not found. Please ensure PostgreSQL client tools are installed.")
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.decode("utf-8", errors="ignore") if e.stderr else ""
                raise RuntimeError(f"pg_dump failed: {stderr.strip() or e}")
        else:
            # Best effort: we continue without DB artifact
            tmp_db_artifact = None

        # Gather metadata
        alembic_rev = _get_alembic_revision(db.session)
        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "db_type": db_type,
            "alembic_revision": alembic_rev,
            "app_version": None,
        }

        # Serialize settings for convenience (DB backup still authoritative)
        settings_obj = Settings.get_settings()
        settings_json = json.dumps(settings_obj.to_dict(), indent=2, sort_keys=True)

        # Write the zip
        with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as zf:
            _write_manifest(zf, manifest)
            if tmp_db_artifact and os.path.exists(tmp_db_artifact):
                arc_name = "db.sqlite" if db_type == "sqlite" else "db.dump"
                zf.write(tmp_db_artifact, arc_name)

            zf.writestr("settings.json", settings_json.encode("utf-8"))

            # Include uploads (e.g., logos)
            uploads_root = os.path.join(app.root_path, "static", "uploads")
            _add_directory_to_zip(zf, uploads_root, "uploads")

        return archive_path
    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


def restore_backup(app, archive_path: str, progress_callback=None) -> tuple[bool, str]:
    """Restore a backup archive.

    Steps:
    - Extract archive to temp dir
    - Restore DB depending on type
    - Copy uploads back
    - Run migrations to head to ensure compatibility with newer code

    Returns: (success, message)
    """
    from app import db
    from time import sleep

    if not archive_path or not os.path.exists(archive_path):
        return False, f"Backup archive not found: {archive_path}"

    db_type, db_uri, sqlite_path = _detect_db_type_and_path(app)
    tmp_dir = tempfile.mkdtemp(prefix="tt_restore_")

    def _progress(label: str, percent: int):
        try:
            if callable(progress_callback):
                progress_callback(label, percent)
        except Exception as e:
            # Log but continue - progress callback failure is not critical
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Progress callback failed: {e}")

    try:
        # Extract archive
        with ZipFile(archive_path, mode="r") as zf:
            zf.extractall(tmp_dir)
        _progress("Archive extracted", 10)

        # Read manifest (optional)
        manifest_path = os.path.join(tmp_dir, "manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    _ = json.load(f)
            except Exception as e:
                # Log but continue - manifest reading failure is not critical
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Failed to read backup manifest: {e}")

        # Proactively close any open DB connections before modifying files
        try:
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
        except Exception:
            pass

        # Restore DB
        if db_type == "sqlite":
            src_sqlite = os.path.join(tmp_dir, "db.sqlite")
            if not os.path.exists(src_sqlite):
                return False, "Backup does not contain db.sqlite for SQLite restore"

            if not sqlite_path:
                return False, "Current configuration is not SQLite or path not found"

            # Ensure destination directory exists
            dest_dir = os.path.dirname(sqlite_path)
            if dest_dir and not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)

            # Safety copy of current DB if exists
            if os.path.exists(sqlite_path):
                safety_copy = sqlite_path + f".bak_{_now_timestamp()}"
                shutil.copy2(sqlite_path, safety_copy)

            # Replace DB file
            os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
            # Retry a few times in case the file is briefly locked
            last_err = None
            for _ in range(3):
                try:
                    shutil.copy2(src_sqlite, sqlite_path)
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    sleep(0.2)
            if last_err:
                return False, f"Failed to write SQLite database file: {last_err}"
            _progress("SQLite database restored", 60)

        elif db_type == "postgresql":
            src_dump = os.path.join(tmp_dir, "db.dump")
            if not os.path.exists(src_dump):
                return False, "Backup does not contain db.dump for PostgreSQL restore"

            database_url = os.getenv("DATABASE_URL", db_uri)
            parsed = urlparse(database_url) if database_url else None
            host = parsed.hostname if parsed and parsed.hostname else os.getenv("POSTGRES_HOST", "db")
            port = parsed.port if parsed and parsed.port else int(os.getenv("POSTGRES_PORT", "5432"))
            user = parsed.username if parsed and parsed.username else os.getenv("POSTGRES_USER", "timetracker")
            password = parsed.password if parsed and parsed.password else os.getenv("POSTGRES_PASSWORD", "timetracker")
            dbname = parsed.path.lstrip("/") if parsed and parsed.path else os.getenv("POSTGRES_DB", "timetracker")

            pg_restore_cmd = [
                "pg_restore",
                "--clean",
                "--if-exists",
                "--no-owner",
                "-h",
                host,
                "-p",
                str(port),
                "-U",
                user,
                "-d",
                dbname,
                src_dump,
            ]
            env = os.environ.copy()
            if password:
                env["PGPASSWORD"] = str(password)
            try:
                _progress("Restoring PostgreSQL database", 20)
                subprocess.run(pg_restore_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            except FileNotFoundError:
                return False, "pg_restore not found. Please install PostgreSQL client tools."
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.decode("utf-8", errors="ignore") if e.stderr else ""
                return False, f"pg_restore failed: {stderr.strip() or e}"
            _progress("PostgreSQL database restored", 60)
        else:
            return False, "Unsupported or unknown database type for restore"

        # Restore uploads
        extracted_uploads = os.path.join(tmp_dir, "uploads")
        if os.path.isdir(extracted_uploads):
            target_uploads = os.path.join(app.root_path, "static", "uploads")
            os.makedirs(target_uploads, exist_ok=True)
            # Merge copy
            for root, _, files in os.walk(extracted_uploads):
                rel = os.path.relpath(root, extracted_uploads)
                target_dir = os.path.join(target_uploads, rel) if rel != "." else target_uploads
                os.makedirs(target_dir, exist_ok=True)
                for fn in files:
                    shutil.copy2(os.path.join(root, fn), os.path.join(target_dir, fn))
        _progress("Uploads restored", 80)

        # Run migrations to ensure compatibility with current code
        try:
            from flask_migrate import upgrade as alembic_upgrade

            with app.app_context():
                _progress("Running migrations", 90)
                alembic_upgrade()
        except Exception as e:
            # If migrations fail, report failure to caller for visibility
            return False, f"Restore completed but migration failed: {e}"

        # Dispose connections once more after restore/migrate to ensure clean state
        try:
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
        except Exception:
            pass

        _progress("Restore completed successfully", 100)
        return True, "Restore completed successfully"
    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
