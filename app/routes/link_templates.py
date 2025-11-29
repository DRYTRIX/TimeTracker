"""Link Template routes for managing URL templates"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import LinkTemplate
from app.utils.db import safe_commit
from app.utils.permissions import admin_or_permission_required
from datetime import datetime

link_templates_bp = Blueprint("link_templates", __name__)


@link_templates_bp.route("/admin/link-templates")
@login_required
@admin_or_permission_required("manage_settings")
def list_link_templates():
    """List all link templates"""
    templates = LinkTemplate.query.order_by(LinkTemplate.order, LinkTemplate.name).all()
    return render_template("admin/link_templates/list.html", templates=templates)


@link_templates_bp.route("/admin/link-templates/create", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_settings")
def create_link_template():
    """Create a new link template"""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        url_template = request.form.get("url_template", "").strip()
        icon = request.form.get("icon", "").strip()
        field_key = request.form.get("field_key", "").strip()
        is_active = request.form.get("is_active") == "on"
        order = request.form.get("order", "0", type=int)

        # Validate required fields
        if not name:
            flash(_("Template name is required"), "error")
            return render_template("admin/link_templates/form.html", template=None)

        if not url_template:
            flash(_("URL template is required"), "error")
            return render_template("admin/link_templates/form.html", template=None)

        if "{value}" not in url_template:
            flash(_("URL template must contain {value} placeholder"), "error")
            return render_template("admin/link_templates/form.html", template=None)

        if not field_key:
            flash(_("Field key is required"), "error")
            return render_template("admin/link_templates/form.html", template=None)

        # Create template
        template = LinkTemplate(
            name=name,
            description=description,
            url_template=url_template,
            icon=icon or "fas fa-external-link-alt",
            field_key=field_key,
            is_active=is_active,
            order=order,
            created_by=current_user.id,
        )

        db.session.add(template)
        if not safe_commit("create_link_template", {"name": name}):
            flash(_("Could not create link template due to a database error."), "error")
            return render_template("admin/link_templates/form.html", template=None)

        flash(_("Link template created successfully"), "success")
        return redirect(url_for("link_templates.list_link_templates"))

    return render_template("admin/link_templates/form.html", template=None)


@link_templates_bp.route("/admin/link-templates/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_settings")
def edit_link_template(template_id):
    """Edit a link template"""
    template = LinkTemplate.query.get_or_404(template_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        url_template = request.form.get("url_template", "").strip()
        icon = request.form.get("icon", "").strip()
        field_key = request.form.get("field_key", "").strip()
        is_active = request.form.get("is_active") == "on"
        order = request.form.get("order", "0", type=int)

        # Validate required fields
        if not name:
            flash(_("Template name is required"), "error")
            return render_template("admin/link_templates/form.html", template=template)

        if not url_template:
            flash(_("URL template is required"), "error")
            return render_template("admin/link_templates/form.html", template=template)

        if "{value}" not in url_template:
            flash(_("URL template must contain {value} placeholder"), "error")
            return render_template("admin/link_templates/form.html", template=template)

        if not field_key:
            flash(_("Field key is required"), "error")
            return render_template("admin/link_templates/form.html", template=template)

        # Update template
        template.name = name
        template.description = description
        template.url_template = url_template
        template.icon = icon or "fas fa-external-link-alt"
        template.field_key = field_key
        template.is_active = is_active
        template.order = order
        template.updated_at = datetime.utcnow()

        if not safe_commit("edit_link_template", {"template_id": template.id}):
            flash(_("Could not update link template due to a database error."), "error")
            return render_template("admin/link_templates/form.html", template=template)

        flash(_("Link template updated successfully"), "success")
        return redirect(url_for("link_templates.list_link_templates"))

    return render_template("admin/link_templates/form.html", template=template)


@link_templates_bp.route("/admin/link-templates/<int:template_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("manage_settings")
def delete_link_template(template_id):
    """Delete a link template"""
    template = LinkTemplate.query.get_or_404(template_id)

    db.session.delete(template)
    if not safe_commit("delete_link_template", {"template_id": template.id}):
        flash(_("Could not delete link template due to a database error."), "error")
    else:
        flash(_("Link template deleted successfully"), "success")

    return redirect(url_for("link_templates.list_link_templates"))

