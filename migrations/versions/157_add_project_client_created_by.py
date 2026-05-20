"""Add created_by to clients and projects for per-user workspace scope.

Revision ID: 157_add_project_client_created_by
Revises: 156_add_user_theme_columns
Create Date: 2026-05-20
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "157_add_project_client_created_by"
down_revision = "156_add_user_theme_columns"
branch_labels = None
depends_on = None

_OWN_SCOPE_PERMISSIONS = [
    "view_own_projects",
    "view_all_projects",
    "edit_own_projects",
    "edit_all_projects",
    "delete_own_projects",
    "delete_all_projects",
    "view_own_clients",
    "view_all_clients",
    "edit_own_clients",
    "edit_all_clients",
    "delete_own_clients",
    "delete_all_clients",
]

_LEGACY_VIEW_PERMS_TO_REMOVE = ("view_projects", "view_clients")


def _table_has_column(inspector, table_name, column_name):
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {c["name"] for c in inspector.get_columns(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _table_has_column(inspector, "clients", "created_by"):
        op.add_column(
            "clients",
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_clients_created_by", "clients", ["created_by"], unique=False)

    if not _table_has_column(inspector, "projects", "created_by"):
        op.add_column(
            "projects",
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_projects_created_by", "projects", ["created_by"], unique=False)

    _seed_own_scope_permissions(bind)
    _update_system_roles(bind)


def _seed_own_scope_permissions(connection):
    """Insert new permissions if missing."""
    perm_defs = [
        ("view_own_projects", "View own projects", "projects"),
        ("view_all_projects", "View all projects", "projects"),
        ("edit_own_projects", "Edit own projects", "projects"),
        ("edit_all_projects", "Edit all projects", "projects"),
        ("delete_own_projects", "Delete own projects", "projects"),
        ("delete_all_projects", "Delete all projects", "projects"),
        ("view_own_clients", "View own clients", "clients"),
        ("view_all_clients", "View all clients", "clients"),
        ("edit_own_clients", "Edit own clients", "clients"),
        ("edit_all_clients", "Edit all clients", "clients"),
        ("delete_own_clients", "Delete own clients", "clients"),
        ("delete_all_clients", "Delete all clients", "clients"),
    ]
    for name, description, category in perm_defs:
        exists = connection.execute(
            sa.text("SELECT id FROM permissions WHERE name = :name"), {"name": name}
        ).fetchone()
        if not exists:
            connection.execute(
                sa.text(
                    "INSERT INTO permissions (name, description, category) VALUES (:name, :description, :category)"
                ),
                {"name": name, "description": description, "category": category},
            )


def _update_system_roles(connection):
    """Grant own-scope perms to user/viewer; view_all to manager/admin; strip broad view from user/viewer."""
    role_perm_map = {
        "user": [
            "view_own_projects",
            "view_own_clients",
        ],
        "viewer": [
            "view_own_projects",
            "view_own_clients",
        ],
        "manager": [
            "view_all_projects",
            "view_all_clients",
            "edit_all_projects",
            "edit_all_clients",
            "delete_all_projects",
            "delete_all_clients",
        ],
        "admin": [
            "view_all_projects",
            "view_all_clients",
            "edit_all_projects",
            "edit_all_clients",
            "delete_all_projects",
            "delete_all_clients",
        ],
    }

    for role_name, perm_names in role_perm_map.items():
        role_row = connection.execute(
            sa.text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}
        ).fetchone()
        if not role_row:
            continue
        role_id = role_row[0]
        for perm_name in perm_names:
            perm_row = connection.execute(
                sa.text("SELECT id FROM permissions WHERE name = :name"), {"name": perm_name}
            ).fetchone()
            if not perm_row:
                continue
            perm_id = perm_row[0]
            exists = connection.execute(
                sa.text(
                    "SELECT 1 FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"
                ),
                {"role_id": role_id, "perm_id": perm_id},
            ).fetchone()
            if not exists:
                connection.execute(
                    sa.text(
                        "INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :perm_id)"
                    ),
                    {"role_id": role_id, "perm_id": perm_id},
                )

    for role_name in ("user", "viewer"):
        role_row = connection.execute(
            sa.text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}
        ).fetchone()
        if not role_row:
            continue
        role_id = role_row[0]
        for perm_name in _LEGACY_VIEW_PERMS_TO_REMOVE:
            perm_row = connection.execute(
                sa.text("SELECT id FROM permissions WHERE name = :name"), {"name": perm_name}
            ).fetchone()
            if not perm_row:
                continue
            connection.execute(
                sa.text(
                    "DELETE FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"
                ),
                {"role_id": role_id, "perm_id": perm_row[0]},
            )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    for role_name in ("user", "viewer"):
        role_row = bind.execute(sa.text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}).fetchone()
        if not role_row:
            continue
        role_id = role_row[0]
        for perm_name in _LEGACY_VIEW_PERMS_TO_REMOVE:
            perm_row = bind.execute(
                sa.text("SELECT id FROM permissions WHERE name = :name"), {"name": perm_name}
            ).fetchone()
            if not perm_row:
                continue
            exists = bind.execute(
                sa.text(
                    "SELECT 1 FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"
                ),
                {"role_id": role_id, "perm_id": perm_row[0]},
            ).fetchone()
            if not exists:
                bind.execute(
                    sa.text(
                        "INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :perm_id)"
                    ),
                    {"role_id": role_id, "perm_id": perm_row[0]},
                )

    if "permissions" in inspector.get_table_names():
        for name in _OWN_SCOPE_PERMISSIONS:
            bind.execute(sa.text("DELETE FROM permissions WHERE name = :name"), {"name": name})

    if _table_has_column(inspector, "projects", "created_by"):
        op.drop_index("ix_projects_created_by", table_name="projects")
        op.drop_column("projects", "created_by")
    if _table_has_column(inspector, "clients", "created_by"):
        op.drop_index("ix_clients_created_by", table_name="clients")
        op.drop_column("clients", "created_by")
