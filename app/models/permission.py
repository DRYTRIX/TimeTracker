"""Permission model for granular access control"""

from datetime import datetime
from app import db


class Permission(db.Model):
    """Permission model - represents a single permission in the system"""

    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    category = db.Column(
        db.String(50), nullable=False, index=True
    )  # e.g., 'time_entries', 'projects', 'users', 'reports', 'system'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, name, description=None, category="general"):
        self.name = name
        self.description = description
        self.category = category

    def __repr__(self):
        return f"<Permission {self.name}>"

    def to_dict(self):
        """Convert permission to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Association table for many-to-many relationship between roles and permissions
role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    db.Column("created_at", db.DateTime, default=datetime.utcnow, nullable=False),
)


class Role(db.Model):
    """Role model - bundles permissions together"""

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    is_system_role = db.Column(db.Boolean, default=False, nullable=False)  # System roles cannot be deleted
    # Role-based module visibility: module IDs hidden for this role (denylist).
    # Empty/None means no modules are hidden.
    hidden_module_ids = db.Column(db.JSON, default=list, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    permissions = db.relationship(
        "Permission", secondary=role_permissions, lazy="joined", backref=db.backref("roles", lazy="dynamic")
    )

    def __init__(self, name, description=None, is_system_role=False, hidden_module_ids=None):
        self.name = name
        self.description = description
        self.is_system_role = is_system_role
        if hidden_module_ids is not None:
            self.hidden_module_ids = hidden_module_ids

    def __repr__(self):
        return f"<Role {self.name}>"

    def has_permission(self, permission_name):
        """Check if role has a specific permission"""
        return any(p.name == permission_name for p in self.permissions)

    def add_permission(self, permission):
        """Add a permission to this role"""
        if not self.has_permission(permission.name):
            self.permissions.append(permission)

    def remove_permission(self, permission):
        """Remove a permission from this role"""
        if self.has_permission(permission.name):
            self.permissions.remove(permission)

    def get_permission_names(self):
        """Get list of permission names for this role"""
        return [p.name for p in self.permissions]

    def to_dict(self, include_permissions=False):
        """Convert role to dictionary"""
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_system_role": self.is_system_role,
            "hidden_module_ids": (self.hidden_module_ids if self.hidden_module_ids is not None else []),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_permissions:
            data["permissions"] = [p.to_dict() for p in self.permissions]
            data["permission_count"] = len(self.permissions)
        return data


# Association table for many-to-many relationship between users and roles
user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("assigned_at", db.DateTime, default=datetime.utcnow, nullable=False),
)
