"""Routes for role and permission management (admin only)"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, limiter
from app.models import Permission, Role, User
from app.utils.permissions import admin_or_permission_required
from app.utils.db import safe_commit
from app.utils.permissions_seed import sync_permissions_and_roles
from app.utils.module_registry import ModuleRegistry, ModuleCategory
from sqlalchemy.exc import IntegrityError

permissions_bp = Blueprint("permissions", __name__)


def _get_modules_by_category_for_roles():
    """
    Return a stable, ordered list of (category, modules[]) for role module-visibility UI.

    Notes:
    - Core modules are excluded (always enabled).
    - Registry init is idempotent.
    """
    ModuleRegistry.initialize_defaults()
    categories = [c for c in ModuleCategory if c != ModuleCategory.CORE]
    return [(category, ModuleRegistry.get_by_category(category)) for category in categories]


def _sanitize_hidden_module_ids(module_ids):
    """Filter/normalize hidden module IDs coming from forms."""
    ModuleRegistry.initialize_defaults()
    hidden = []
    for module_id in module_ids or []:
        module = ModuleRegistry.get(module_id)
        if not module:
            continue
        if module.category == ModuleCategory.CORE:
            continue
        if module_id not in hidden:
            hidden.append(module_id)
    return hidden


@permissions_bp.route("/admin/roles")
@login_required
@admin_or_permission_required("manage_roles")
def list_roles():
    """List all roles"""

    # Auto-sync permissions and roles to ensure they're up to date
    sync_permissions_and_roles()

    roles = Role.query.order_by(Role.name).all()
    return render_template("admin/roles/list.html", roles=roles)


@permissions_bp.route("/admin/roles/create", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_roles")
def create_role():
    """Create a new role"""
    # Check if user has permission to manage roles
    if not current_user.is_admin and not current_user.has_permission("manage_roles"):
        flash(_("You do not have permission to access this page"), "error")
        return redirect(url_for("main.dashboard"))

    modules_by_category = _get_modules_by_category_for_roles()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash(_("Role name is required"), "error")
            return render_template(
                "admin/roles/form.html",
                role=None,
                all_permissions=Permission.query.all(),
                modules_by_category=modules_by_category,
            )

        # Check if role already exists
        if Role.query.filter_by(name=name).first():
            flash(_("A role with this name already exists"), "error")
            return render_template(
                "admin/roles/form.html",
                role=None,
                all_permissions=Permission.query.all(),
                modules_by_category=modules_by_category,
            )

        # Create role
        role = Role(name=name, description=description, is_system_role=False)
        db.session.add(role)

        # Assign selected permissions
        permission_ids = request.form.getlist("permissions")
        for perm_id in permission_ids:
            permission = Permission.query.get(int(perm_id))
            if permission:
                role.add_permission(permission)

        # Assign hidden modules (denylist)
        role.hidden_module_ids = _sanitize_hidden_module_ids(request.form.getlist("hidden_modules"))

        if not safe_commit("create_role", {"name": name}):
            flash(_("Could not create role due to a database error"), "error")
            return render_template(
                "admin/roles/form.html",
                role=None,
                all_permissions=Permission.query.all(),
                modules_by_category=modules_by_category,
            )

        flash(_("Role created successfully"), "success")
        return redirect(url_for("permissions.list_roles"))

    # GET request
    all_permissions = Permission.query.order_by(Permission.category, Permission.name).all()
    return render_template(
        "admin/roles/form.html",
        role=None,
        all_permissions=all_permissions,
        modules_by_category=modules_by_category,
    )


@permissions_bp.route("/admin/roles/<int:role_id>/edit", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_roles")
def edit_role(role_id):
    """Edit an existing role"""
    # Check if user has permission to manage roles
    if not current_user.is_admin and not current_user.has_permission("manage_roles"):
        flash(_("You do not have permission to access this page"), "error")
        return redirect(url_for("main.dashboard"))

    role = Role.query.get_or_404(role_id)

    modules_by_category = _get_modules_by_category_for_roles()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash(_("Role name is required"), "error")
            return render_template(
                "admin/roles/form.html",
                role=role,
                all_permissions=Permission.query.all(),
                modules_by_category=modules_by_category,
            )

        # For system roles, don't allow name changes (name is the identifier)
        if role.is_system_role and name != role.name:
            flash(_("System role names cannot be changed"), "error")
            return render_template(
                "admin/roles/form.html",
                role=role,
                all_permissions=Permission.query.all(),
                modules_by_category=modules_by_category,
            )

        # Check if name is taken by another role
        existing = Role.query.filter_by(name=name).first()
        if existing and existing.id != role.id:
            flash(_("A role with this name already exists"), "error")
            return render_template(
                "admin/roles/form.html",
                role=role,
                all_permissions=Permission.query.all(),
                modules_by_category=modules_by_category,
            )

        # Update role
        if not role.is_system_role:
            role.name = name
        role.description = description

        # Update permissions
        permission_ids = request.form.getlist("permissions")
        # Remove all current permissions
        role.permissions = []
        # Add selected permissions
        for perm_id in permission_ids:
            permission = Permission.query.get(int(perm_id))
            if permission:
                role.add_permission(permission)

        # Update hidden modules (denylist)
        role.hidden_module_ids = _sanitize_hidden_module_ids(request.form.getlist("hidden_modules"))

        if not safe_commit("edit_role", {"role_id": role.id}):
            flash(_("Could not update role due to a database error"), "error")
            return render_template(
                "admin/roles/form.html",
                role=role,
                all_permissions=Permission.query.all(),
                modules_by_category=modules_by_category,
            )

        flash(_("Role updated successfully"), "success")
        return redirect(url_for("permissions.view_role", role_id=role.id))

    # GET request - auto-sync before showing form
    sync_permissions_and_roles()
    all_permissions = Permission.query.order_by(Permission.category, Permission.name).all()
    return render_template(
        "admin/roles/form.html",
        role=role,
        all_permissions=all_permissions,
        modules_by_category=modules_by_category,
    )


@permissions_bp.route("/admin/roles/<int:role_id>")
@login_required
@admin_or_permission_required("manage_roles")
def view_role(role_id):
    """View role details"""
    # Check if user has permission to view roles
    if not current_user.is_admin and not current_user.has_permission("view_permissions"):
        flash(_("You do not have permission to access this page"), "error")
        return redirect(url_for("main.dashboard"))

    role = Role.query.get_or_404(role_id)
    users = role.users.all()
    return render_template("admin/roles/view.html", role=role, users=users)


@permissions_bp.route("/admin/roles/<int:role_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("manage_roles")
@limiter.limit("10 per minute")
def delete_role(role_id):
    """Delete a role"""
    # Check if user has permission to manage roles
    if not current_user.is_admin and not current_user.has_permission("manage_roles"):
        flash(_("You do not have permission to perform this action"), "error")
        return redirect(url_for("main.dashboard"))

    role = Role.query.get_or_404(role_id)

    # Prevent deleting system roles
    if role.is_system_role:
        flash(_("System roles cannot be deleted"), "error")
        return redirect(url_for("permissions.list_roles"))

    # Check if role is assigned to any users
    if role.users.count() > 0:
        flash(_("Cannot delete role that is assigned to users. Please reassign users first."), "error")
        return redirect(url_for("permissions.view_role", role_id=role.id))

    role_name = role.name
    db.session.delete(role)

    if not safe_commit("delete_role", {"role_id": role.id}):
        flash(_("Could not delete role due to a database error"), "error")
        return redirect(url_for("permissions.list_roles"))

    flash(_('Role "%(name)s" deleted successfully', name=role_name), "success")
    return redirect(url_for("permissions.list_roles"))


@permissions_bp.route("/admin/permissions")
@login_required
@admin_or_permission_required("manage_roles")
def list_permissions():
    """List all permissions"""
    # Check if user has permission to view permissions
    if not current_user.is_admin and not current_user.has_permission("view_permissions"):
        flash(_("You do not have permission to access this page"), "error")
        return redirect(url_for("main.dashboard"))

    # Auto-sync permissions and roles to ensure they're up to date
    sync_permissions_and_roles()

    # Group permissions by category
    permissions = Permission.query.order_by(Permission.category, Permission.name).all()

    # Organize by category
    permissions_by_category = {}
    for perm in permissions:
        category = perm.category or "general"
        if category not in permissions_by_category:
            permissions_by_category[category] = []
        permissions_by_category[category].append(perm)

    return render_template("admin/permissions/list.html", permissions_by_category=permissions_by_category)


@permissions_bp.route("/admin/users/<int:user_id>/roles", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_roles")
def manage_user_roles(user_id):
    """Manage roles for a specific user"""
    # Check if user has permission to manage user roles
    if not current_user.is_admin and not current_user.has_permission("manage_user_roles"):
        flash(_("You do not have permission to access this page"), "error")
        return redirect(url_for("main.dashboard"))

    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        # Get selected role IDs
        role_ids = request.form.getlist("roles")

        # Validate role assignments - only super_admins can assign super_admin roles
        # and only super_admins can remove admin roles
        is_super_admin = current_user.is_super_admin
        selected_roles = [Role.query.get(int(role_id)) for role_id in role_ids if role_id]
        selected_roles = [r for r in selected_roles if r]  # Remove None values
        
        # Check if trying to assign super_admin role
        has_super_admin = any(r.name == "super_admin" for r in selected_roles)
        if has_super_admin and not is_super_admin:
            flash(_("Only Super Admins can assign the super_admin role"), "error")
            all_roles = Role.query.order_by(Role.name).all()
            return render_template("admin/users/roles.html", user=user, all_roles=all_roles)
        
        # Check if trying to remove admin role from self
        current_has_admin = any(r.name == "admin" for r in user.roles)
        new_has_admin = any(r.name == "admin" for r in selected_roles)
        if current_has_admin and not new_has_admin and user.id == current_user.id and not is_super_admin:
            flash(_("Only Super Admins can remove the admin role from themselves"), "error")
            all_roles = Role.query.order_by(Role.name).all()
            return render_template("admin/users/roles.html", user=user, all_roles=all_roles)
        
        # Check if trying to remove admin role from another user
        if current_has_admin and not new_has_admin and user.id != current_user.id and not is_super_admin:
            flash(_("Only Super Admins can remove the admin role from other users"), "error")
            all_roles = Role.query.order_by(Role.name).all()
            return render_template("admin/users/roles.html", user=user, all_roles=all_roles)

        # Clear current roles
        user.roles = []

        # Assign selected roles
        primary_role_name = None
        for role in selected_roles:
            user.add_role(role)
            # Use the first role as the primary role for backward compatibility
            if primary_role_name is None:
                primary_role_name = role.name

        # Update legacy role field for backward compatibility
        # This ensures the old role field stays in sync with the new role system
        if primary_role_name:
            user.role = primary_role_name

        if not safe_commit("manage_user_roles", {"user_id": user.id}):
            flash(_("Could not update user roles due to a database error"), "error")
            return render_template("admin/users/roles.html", user=user, all_roles=Role.query.all())

        flash(_("User roles updated successfully"), "success")
        return redirect(url_for("admin.edit_user", user_id=user.id))

    # GET request
    all_roles = Role.query.order_by(Role.name).all()
    return render_template("admin/users/roles.html", user=user, all_roles=all_roles)


@permissions_bp.route("/api/users/<int:user_id>/permissions")
@login_required
def get_user_permissions(user_id):
    """API endpoint to get user's effective permissions"""
    # Users can view their own permissions, admins can view any user's permissions
    if current_user.id != user_id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(user_id)
    permissions = user.get_all_permissions()

    return jsonify(
        {
            "user_id": user.id,
            "username": user.username,
            "roles": [{"id": r.id, "name": r.name} for r in user.roles],
            "permissions": [{"id": p.id, "name": p.name, "description": p.description} for p in permissions],
        }
    )


@permissions_bp.route("/api/roles/<int:role_id>/permissions")
@login_required
@admin_or_permission_required("manage_roles")
def get_role_permissions(role_id):
    """API endpoint to get role's permissions"""
    role = Role.query.get_or_404(role_id)

    return jsonify(
        {
            "role_id": role.id,
            "name": role.name,
            "description": role.description,
            "is_system_role": role.is_system_role,
            "permissions": [
                {"id": p.id, "name": p.name, "description": p.description, "category": p.category}
                for p in role.permissions
            ],
        }
    )
