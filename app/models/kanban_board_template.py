from app import db
from app.utils.timezone import now_in_app_timezone

# Fields copied from a KanbanColumn into a template snapshot. is_system is
# deliberately excluded: applying a template always creates user-owned
# (non-system) columns.
_COLUMN_SPEC_FIELDS = (
    "key",
    "label",
    "icon",
    "color",
    "position",
    "is_complete_state",
)

# Column attributes captured only when the running schema actually has them, so
# templates stay decoupled from optional features that add columns to
# KanbanColumn (e.g. per-column WIP limits).
_OPTIONAL_COLUMN_SPEC_FIELDS = ("wip_limit",)


class KanbanBoardTemplate(db.Model):
    """A saved, reusable snapshot of a set of kanban columns.

    Templates let an admin capture the column layout of one board (global or
    project-specific) and re-apply it to other projects, so teams don't have
    to hand-build the same "To Do / In Progress / Review / Done" structure
    over and over.
    """

    __tablename__ = "kanban_board_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    # Ordered list of column spec dicts (see _COLUMN_SPEC_FIELDS).
    columns = db.Column(db.JSON, nullable=False, default=list)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=now_in_app_timezone,
        onupdate=now_in_app_timezone,
        nullable=False,
    )

    creator = db.relationship("User")

    def __repr__(self):
        return f"<KanbanBoardTemplate {self.name!r} cols={len(self.columns or [])}>"

    @property
    def column_count(self):
        """Number of columns captured in this template."""
        return len(self.columns or [])

    @staticmethod
    def spec_from_column(column):
        """Build a template column-spec dict from a KanbanColumn instance."""
        spec = {field: getattr(column, field) for field in _COLUMN_SPEC_FIELDS}
        for field in _OPTIONAL_COLUMN_SPEC_FIELDS:
            if hasattr(column, field):
                spec[field] = getattr(column, field)
        return spec

    @classmethod
    def from_columns(cls, name, columns, description=None, created_by=None):
        """Create a template capturing the given ordered KanbanColumn list."""
        specs = [cls.spec_from_column(col) for col in columns]
        return cls(
            name=name.strip(),
            description=(description or None),
            columns=specs,
            created_by=created_by,
        )

    def apply_to_project(self, project_id=None, replace=False):
        """Materialize this template's columns for the given project scope.

        project_id=None targets the global columns. When replace is True the
        scope's existing columns are removed first; otherwise columns whose
        key already exists in the scope are skipped so no unique constraint is
        violated.

        Returns the number of columns created.
        """
        from app.models import KanbanColumn

        if replace:
            existing = KanbanColumn.get_all_columns(project_id=project_id)
            for col in existing:
                db.session.delete(col)
            db.session.flush()
            existing_keys = set()
        else:
            existing_keys = {col.key for col in KanbanColumn.get_all_columns(project_id=project_id)}

        created = 0
        for position, spec in enumerate(self.columns or []):
            key = spec.get("key")
            if not key or key in existing_keys:
                continue
            column = KanbanColumn(
                key=key,
                label=spec.get("label") or key,
                icon=spec.get("icon") or "fas fa-circle",
                color=spec.get("color") or "secondary",
                position=spec.get("position", position),
                is_complete_state=bool(spec.get("is_complete_state")),
                is_system=False,
                is_active=True,
                project_id=project_id,
            )
            for field in _OPTIONAL_COLUMN_SPEC_FIELDS:
                if field in spec and hasattr(KanbanColumn, field):
                    setattr(column, field, spec.get(field))
            db.session.add(column)
            existing_keys.add(key)
            created += 1
        return created

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "columns": self.columns or [],
            "column_count": self.column_count,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
