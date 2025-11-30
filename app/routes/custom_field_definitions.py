"""Custom Field Definition routes for managing global custom field definitions"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import CustomFieldDefinition
from app.utils.db import safe_commit
from app.utils.permissions import admin_or_permission_required
from datetime import datetime

custom_field_definitions_bp = Blueprint("custom_field_definitions", __name__)


@custom_field_definitions_bp.route("/admin/custom-field-definitions")
@login_required
@admin_or_permission_required("manage_settings")
def list_custom_field_definitions():
    """List all custom field definitions"""
    definitions = CustomFieldDefinition.query.order_by(CustomFieldDefinition.order, CustomFieldDefinition.label).all()
    return render_template("admin/custom_field_definitions/list.html", definitions=definitions)


@custom_field_definitions_bp.route("/admin/custom-field-definitions/create", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_settings")
def create_custom_field_definition():
    """Create a new custom field definition"""
    if request.method == "POST":
        field_key = request.form.get("field_key", "").strip()
        label = request.form.get("label", "").strip()
        description = request.form.get("description", "").strip()
        is_mandatory = request.form.get("is_mandatory") == "on"
        is_active = request.form.get("is_active") == "on"
        order = request.form.get("order", "0", type=int)

        # Validate required fields
        if not field_key:
            flash(_("Field key is required"), "error")
            return render_template("admin/custom_field_definitions/form.html", definition=None)

        if not label:
            flash(_("Label is required"), "error")
            return render_template("admin/custom_field_definitions/form.html", definition=None)

        # Validate field_key format (alphanumeric and underscores only)
        if not field_key.replace("_", "").isalnum():
            flash(_("Field key must contain only letters, numbers, and underscores"), "error")
            return render_template("admin/custom_field_definitions/form.html", definition=None)

        # Check for duplicate field_key
        existing = CustomFieldDefinition.query.filter_by(field_key=field_key).first()
        if existing:
            flash(_("A custom field definition with this key already exists"), "error")
            return render_template("admin/custom_field_definitions/form.html", definition=None)

        # Create definition
        definition = CustomFieldDefinition(
            field_key=field_key,
            label=label,
            description=description,
            is_mandatory=is_mandatory,
            is_active=is_active,
            order=order,
            created_by=current_user.id,
        )

        db.session.add(definition)
        if not safe_commit("create_custom_field_definition", {"field_key": field_key}):
            flash(_("Could not create custom field definition due to a database error."), "error")
            return render_template("admin/custom_field_definitions/form.html", definition=None)

        flash(_("Custom field definition created successfully"), "success")
        return redirect(url_for("custom_field_definitions.list_custom_field_definitions"))

    return render_template("admin/custom_field_definitions/form.html", definition=None)


@custom_field_definitions_bp.route("/admin/custom-field-definitions/<int:definition_id>/edit", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_settings")
def edit_custom_field_definition(definition_id):
    """Edit a custom field definition"""
    definition = CustomFieldDefinition.query.get_or_404(definition_id)

    if request.method == "POST":
        field_key = request.form.get("field_key", "").strip()
        label = request.form.get("label", "").strip()
        description = request.form.get("description", "").strip()
        is_mandatory = request.form.get("is_mandatory") == "on"
        is_active = request.form.get("is_active") == "on"
        order = request.form.get("order", "0", type=int)

        # Validate required fields
        if not field_key:
            flash(_("Field key is required"), "error")
            return render_template("admin/custom_field_definitions/form.html", definition=definition)

        if not label:
            flash(_("Label is required"), "error")
            return render_template("admin/custom_field_definitions/form.html", definition=definition)

        # Validate field_key format
        if not field_key.replace("_", "").isalnum():
            flash(_("Field key must contain only letters, numbers, and underscores"), "error")
            return render_template("admin/custom_field_definitions/form.html", definition=definition)

        # Check for duplicate field_key (excluding current definition)
        existing = CustomFieldDefinition.query.filter(
            CustomFieldDefinition.field_key == field_key,
            CustomFieldDefinition.id != definition_id
        ).first()
        if existing:
            flash(_("A custom field definition with this key already exists"), "error")
            return render_template("admin/custom_field_definitions/form.html", definition=definition)

        # Update definition
        definition.field_key = field_key
        definition.label = label
        definition.description = description
        definition.is_mandatory = is_mandatory
        definition.is_active = is_active
        definition.order = order
        definition.updated_at = datetime.utcnow()

        if not safe_commit("edit_custom_field_definition", {"definition_id": definition.id}):
            flash(_("Could not update custom field definition due to a database error."), "error")
            return render_template("admin/custom_field_definitions/form.html", definition=definition)

        flash(_("Custom field definition updated successfully"), "success")
        return redirect(url_for("custom_field_definitions.list_custom_field_definitions"))

    return render_template("admin/custom_field_definitions/form.html", definition=definition)


@custom_field_definitions_bp.route("/admin/custom-field-definitions/<int:definition_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("manage_settings")
def delete_custom_field_definition(definition_id):
    """Delete a custom field definition"""
    definition = CustomFieldDefinition.query.get_or_404(definition_id)

    db.session.delete(definition)
    if not safe_commit("delete_custom_field_definition", {"definition_id": definition.id}):
        flash(_("Could not delete custom field definition due to a database error."), "error")
    else:
        flash(_("Custom field definition deleted successfully"), "success")

    return redirect(url_for("custom_field_definitions.list_custom_field_definitions"))
