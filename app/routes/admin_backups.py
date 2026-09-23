"""Admin routes for backup and restore (registered on admin_bp)."""

import os
import shutil
import threading
import uuid
from datetime import datetime

from flask import current_app, flash, redirect, render_template, request, send_file, url_for
from flask_babel import gettext as _
from flask_login import login_required
from werkzeug.utils import secure_filename

from app import limiter
from app.routes.admin import admin_bp
from app.utils.backup import create_backup, get_backup_root_dir, restore_backup
from app.utils.error_handling import safe_file_remove
from app.utils.permissions import admin_or_permission_required

# In-memory restore progress tracking (simple, per-process)
RESTORE_PROGRESS = {}


@admin_bp.route("/admin/backups")
@login_required
@admin_or_permission_required("manage_backups")
def backups_management():
    """Backups management page"""
    # Get list of existing backups
    backups_dir = get_backup_root_dir(current_app)
    backups = []

    if os.path.exists(backups_dir):
        for filename in os.listdir(backups_dir):
            if filename.endswith(".zip") and not filename.startswith("restore_"):
                filepath = os.path.join(backups_dir, filename)
                stat = os.stat(filepath)
                backups.append(
                    {
                        "filename": filename,
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_mtime),
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    }
                )

    # Sort by creation date (newest first)
    backups.sort(key=lambda x: x["created"], reverse=True)

    return render_template("admin/backups.html", backups=backups, backups_dir=backups_dir)


@admin_bp.route("/admin/backup/create", methods=["POST"])
@login_required
@admin_or_permission_required("manage_backups")
def create_backup_manual():
    """Create manual backup and return the archive for download."""
    try:
        archive_path = create_backup(current_app)
        if not archive_path or not os.path.exists(archive_path):
            flash(_("Backup failed: archive not created"), "error")
            return redirect(url_for("admin.backups_management"))
        # Stream file to user
        return send_file(archive_path, as_attachment=True)
    except Exception as e:
        flash(_("Backup failed: %(error)s", error=str(e)), "error")
        return redirect(url_for("admin.backups_management"))


@admin_bp.route("/admin/backup/download/<filename>")
@login_required
@admin_or_permission_required("manage_backups")
def download_backup(filename):
    """Download an existing backup file"""
    # Security: only allow downloading .zip files, no path traversal
    filename = secure_filename(filename)
    if not filename.endswith(".zip"):
        flash(_("Invalid file type"), "error")
        return redirect(url_for("admin.backups_management"))

    backups_dir = get_backup_root_dir(current_app)
    filepath = os.path.join(backups_dir, filename)

    if not os.path.exists(filepath):
        flash(_("Backup file not found"), "error")
        return redirect(url_for("admin.backups_management"))

    return send_file(filepath, as_attachment=True)


@admin_bp.route("/admin/backup/delete/<filename>", methods=["POST"])
@login_required
@admin_or_permission_required("manage_backups")
def delete_backup(filename):
    """Delete a backup file"""
    # Security: only allow deleting .zip files, no path traversal
    filename = secure_filename(filename)
    if not filename.endswith(".zip"):
        flash(_("Invalid file type"), "error")
        return redirect(url_for("admin.backups_management"))

    backups_dir = get_backup_root_dir(current_app)
    filepath = os.path.join(backups_dir, filename)

    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            flash(_('Backup "%(filename)s" deleted successfully', filename=filename), "success")
        else:
            flash(_("Backup file not found"), "error")
    except Exception as e:
        flash(_("Failed to delete backup: %(error)s", error=str(e)), "error")

    return redirect(url_for("admin.backups_management"))


@admin_bp.route("/admin/restore", methods=["GET", "POST"])
@admin_bp.route("/admin/restore/<filename>", methods=["POST"])
@limiter.limit("3 per minute", methods=["POST"])  # heavy operation
@login_required
@admin_or_permission_required("manage_backups")
def restore(filename=None):
    """Restore from an uploaded backup archive or existing backup file."""
    if request.method == "POST":
        backups_dir = get_backup_root_dir(current_app)

        # If restoring from an existing backup file
        if filename:
            filename = secure_filename(filename)
            if not filename.lower().endswith(".zip"):
                flash(_("Invalid file type. Please select a .zip backup archive."), "error")
                return redirect(url_for("admin.backups_management"))
            temp_path = os.path.join(backups_dir, filename)
            if not os.path.exists(temp_path):
                flash(_("Backup file not found."), "error")
                return redirect(url_for("admin.backups_management"))
            # Copy to temp location for processing
            actual_restore_path = os.path.join(backups_dir, f"restore_{uuid.uuid4().hex[:8]}_{filename}")
            shutil.copy2(temp_path, actual_restore_path)
            temp_path = actual_restore_path
        # If uploading a new backup file
        elif "backup_file" in request.files and request.files["backup_file"].filename != "":
            file = request.files["backup_file"]
            uploaded_filename = secure_filename(file.filename)
            if not uploaded_filename.lower().endswith(".zip"):
                flash(_("Invalid file type. Please upload a .zip backup archive."), "error")
                return redirect(url_for("admin.restore"))
            # Save temporarily under project backups
            os.makedirs(backups_dir, exist_ok=True)
            temp_path = os.path.join(backups_dir, f"restore_{uuid.uuid4().hex[:8]}_{uploaded_filename}")
            file.save(temp_path)
        else:
            flash(_("No backup file provided"), "error")
            return redirect(url_for("admin.restore"))

        # Initialize progress state
        token = uuid.uuid4().hex[:8]
        RESTORE_PROGRESS[token] = {"status": "starting", "percent": 0, "message": "Queued"}

        def progress_cb(label, percent):
            RESTORE_PROGRESS[token] = {"status": "running", "percent": int(percent), "message": label}

        # Capture the real Flask app object for use in a background thread
        app_obj = current_app._get_current_object()

        def _do_restore():
            try:
                RESTORE_PROGRESS[token] = {"status": "running", "percent": 5, "message": "Starting restore"}
                success, message = restore_backup(app_obj, temp_path, progress_callback=progress_cb)
                RESTORE_PROGRESS[token] = {
                    "status": "done" if success else "error",
                    "percent": 100 if success else RESTORE_PROGRESS[token].get("percent", 0),
                    "message": message,
                }
            except Exception as e:
                RESTORE_PROGRESS[token] = {
                    "status": "error",
                    "percent": RESTORE_PROGRESS[token].get("percent", 0),
                    "message": str(e),
                }
            finally:
                safe_file_remove(temp_path, app_obj.logger)

        # Run restore in background to keep request responsive
        t = threading.Thread(target=_do_restore, daemon=True)
        t.start()

        flash(_("Restore started. You can monitor progress on this page."), "info")
        return redirect(url_for("admin.restore", token=token))
    # GET
    token = request.args.get("token")
    progress = RESTORE_PROGRESS.get(token) if token else None
    return render_template("admin/restore.html", progress=progress, token=token)
