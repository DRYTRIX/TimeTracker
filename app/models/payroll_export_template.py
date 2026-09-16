"""Payroll export template presets for workforce CSV/XLSX downloads."""

from datetime import datetime

from app import db


class PayrollExportTemplate(db.Model):
    __tablename__ = "payroll_export_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    columns = db.Column(db.JSON, nullable=False, default=list)
    grouping = db.Column(db.String(20), nullable=False, default="week")  # week|day|project
    filters = db.Column(db.JSON, nullable=True, default=dict)
    format = db.Column(db.String(10), nullable=False, default="csv")  # csv|xlsx
    delimiter = db.Column(db.String(5), nullable=False, default=",")
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    is_builtin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    DEFAULT_COLUMNS = [
        "user_id",
        "username",
        "employee_id",
        "week_year",
        "week_number",
        "period_start",
        "period_end",
        "project_code",
        "hours",
        "billable_hours",
        "non_billable_hours",
        "rate",
        "amount",
        "earning_code",
        "cost_center",
    ]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "columns": self.columns or [],
            "grouping": self.grouping,
            "filters": self.filters or {},
            "format": self.format,
            "delimiter": self.delimiter,
            "is_default": self.is_default,
            "is_builtin": self.is_builtin,
        }

    @classmethod
    def ensure_builtin_defaults(cls):
        """Seed the Generic Payroll preset if missing."""
        existing = cls.query.filter_by(name="Generic Payroll").first()
        if existing:
            return existing
        # Clear other defaults if any
        for t in cls.query.filter_by(is_default=True).all():
            t.is_default = False
        tmpl = cls(
            name="Generic Payroll",
            columns=list(cls.DEFAULT_COLUMNS),
            grouping="week",
            filters={},
            format="csv",
            delimiter=",",
            is_default=True,
            is_builtin=True,
        )
        db.session.add(tmpl)
        db.session.commit()
        return tmpl
