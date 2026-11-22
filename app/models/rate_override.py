from datetime import datetime
from decimal import Decimal

from app import db


class RateOverride(db.Model):
    """Billable rate overrides per project and optionally per user.

    Resolution precedence (highest to lowest) for effective hourly rate:
    - RateOverride for (project_id, user_id)
    - RateOverride for (project_id, user_id=None)  # project default override
    - Project.hourly_rate
    - Client.default_hourly_rate
    - 0
    """

    __tablename__ = "rate_overrides"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    hourly_rate = db.Column(db.Numeric(9, 2), nullable=False)
    effective_from = db.Column(db.Date, nullable=True)
    effective_to = db.Column(db.Date, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("project_id", "user_id", "effective_from", name="ux_rate_override_unique_window"),
    )

    @classmethod
    def resolve_rate(cls, project, user_id=None, on_date=None):
        """Resolve effective hourly rate for a project/user at a given date."""
        rate, _source = cls.resolve_rate_with_source(project, user_id=user_id, on_date=on_date)
        return rate

    @classmethod
    def resolve_rate_with_source(cls, project, user_id=None, on_date=None):
        """Resolve the effective hourly rate and report where it came from.

        Returns ``(rate, source)``. ``source`` is one of ``"user_override"``,
        ``"project_override"``, ``"project"``, ``"client"``, or ``None`` when no
        rate is configured anywhere in the chain (``rate`` is then ``Decimal("0")``).
        """
        if not project:
            return Decimal("0"), None

        # Step 1: specific user override
        if user_id is not None:
            user_ovr = cls._override_query(project.id, user_id, on_date).first()
            if user_ovr:
                return Decimal(user_ovr.hourly_rate), "user_override"

        # Step 2: project-level override
        proj_ovr = cls._override_query(project.id, None, on_date).first()
        if proj_ovr:
            return Decimal(proj_ovr.hourly_rate), "project_override"

        # Step 3: project rate
        if project.hourly_rate:
            return Decimal(project.hourly_rate), "project"

        # Step 4: client default
        try:
            if project.client_obj and project.client_obj.default_hourly_rate:
                return Decimal(project.client_obj.default_hourly_rate), "client"
        except Exception:
            pass

        return Decimal("0"), None

    @classmethod
    def _override_query(cls, project_id, user_id, on_date):
        q = cls.query.filter_by(project_id=project_id, user_id=user_id)
        if on_date:
            q = q.filter(
                (cls.effective_from.is_(None) | (cls.effective_from <= on_date))
                & (cls.effective_to.is_(None) | (cls.effective_to >= on_date))
            )
        return q.order_by(cls.effective_from.desc().nullslast())
