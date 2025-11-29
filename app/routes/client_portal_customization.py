"""
Client Portal Customization routes
"""

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    send_from_directory,
    current_app,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.client_portal_customization import ClientPortalCustomization
from app.models import Client
from flask_babel import gettext as _
import os
import uuid
from PIL import Image

client_portal_customization_bp = Blueprint("client_portal_customization", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "svg", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_upload_folder():
    """Get folder for portal customization uploads"""
    folder = os.path.join(current_app.root_path, "static", "uploads", "portal_customization")
    os.makedirs(folder, exist_ok=True)
    return folder


@client_portal_customization_bp.route("/admin/clients/<int:client_id>/portal-customization")
@login_required
def edit_customization(client_id):
    """Edit client portal customization"""
    if not current_user.is_admin:
        flash(_("Access denied"), "error")
        return redirect(url_for("main.dashboard"))

    client = Client.query.get_or_404(client_id)
    customization = ClientPortalCustomization.query.filter_by(client_id=client_id).first()

    if not customization:
        customization = ClientPortalCustomization(client_id=client_id)
        db.session.add(customization)
        db.session.commit()

    return render_template("admin/client_portal_customization.html", client=client, customization=customization)


@client_portal_customization_bp.route("/admin/clients/<int:client_id>/portal-customization", methods=["POST"])
@login_required
def update_customization(client_id):
    """Update client portal customization"""
    if not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    client = Client.query.get_or_404(client_id)
    customization = ClientPortalCustomization.query.filter_by(client_id=client_id).first()

    if not customization:
        customization = ClientPortalCustomization(client_id=client_id)
        db.session.add(customization)

    data = request.get_json() if request.is_json else request.form

    # Update fields
    customization.primary_color = data.get("primary_color") or None
    customization.secondary_color = data.get("secondary_color") or None
    customization.accent_color = data.get("accent_color") or None
    customization.font_family = data.get("font_family") or None
    customization.heading_font = data.get("heading_font") or None
    customization.custom_css = data.get("custom_css") or None
    customization.custom_header_html = data.get("custom_header_html") or None
    customization.custom_footer_html = data.get("custom_footer_html") or None
    customization.portal_title = data.get("portal_title") or None
    customization.portal_description = data.get("portal_description") or None
    customization.welcome_message = data.get("welcome_message") or None
    customization.show_projects = bool(data.get("show_projects", True))
    customization.show_invoices = bool(data.get("show_invoices", True))
    customization.show_time_entries = bool(data.get("show_time_entries", True))
    customization.show_quotes = bool(data.get("show_quotes", True))
    customization.logo_url = data.get("logo_url") or None

    # Handle logo upload
    if "logo" in request.files:
        file = request.files["logo"]
        if file and file.filename and allowed_file(file.filename):
            try:
                # Validate file size
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)

                if file_size > MAX_FILE_SIZE:
                    if request.is_json:
                        return jsonify({"error": "File too large. Maximum 5MB."}), 400
                    flash(_("File too large. Maximum 5MB."), "error")
                    return redirect(url_for("client_portal_customization.edit_customization", client_id=client_id))

                # Process and save image
                filename = f"logo_{client_id}_{uuid.uuid4().hex[:8]}.{file.filename.rsplit('.', 1)[1].lower()}"
                upload_folder = get_upload_folder()
                filepath = os.path.join(upload_folder, filename)

                # Open and process image
                img = Image.open(file.stream)
                img.verify()
                file.stream.seek(0)

                # Save original
                img = Image.open(file.stream)
                img.save(filepath, optimize=True, quality=85)

                customization.logo_upload_path = f"/uploads/portal_customization/{filename}"
            except Exception as e:
                current_app.logger.error(f"Error processing logo upload: {e}")
                if request.is_json:
                    return jsonify({"error": "Error processing image"}), 400

    db.session.commit()

    if request.is_json:
        return jsonify({"success": True, "customization": customization.to_dict()})

    flash(_("Portal customization updated successfully"), "success")
    return redirect(url_for("client_portal_customization.edit_customization", client_id=client_id))


@client_portal_customization_bp.route("/uploads/portal_customization/<path:filename>")
def serve_portal_upload(filename):
    """Serve uploaded portal customization files"""
    folder = get_upload_folder()
    return send_from_directory(folder, filename)
