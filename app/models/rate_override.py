from datetime import date, datetime
from decimal import Decimal
from typing import Optional

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

    project = db.relationship("Project", backref=db.backref("rate_overrides", lazy="dynamic"))
    user = db.relationship("User", backref=db.backref("rate_overrides", lazy="dynamic"))

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

    @staticmethod
    def _ranges_overlap(
        a_from: Optional[date],
        a_to: Optional[date],
        b_from: Optional[date],
        b_to: Optional[date],
    ) -> bool:
        """Return True if two inclusive date ranges overlap (None = unbounded)."""
        start_a = a_from or date.min
        end_a = a_to or date.max
        start_b = b_from or date.min
        end_b = b_to or date.max
        return start_a <= end_b and start_b <= end_a

    @classmethod
    def has_overlapping_window(
        cls,
        project_id: int,
        user_id: Optional[int],
        effective_from: Optional[date],
        effective_to: Optional[date],
        exclude_id: Optional[int] = None,
    ) -> bool:
        """True if another override for the same project+person overlaps this window."""
        q = cls.query.filter_by(project_id=project_id, user_id=user_id)
        if exclude_id is not None:
            q = q.filter(cls.id != exclude_id)
        for existing in q.all():
            if cls._ranges_overlap(
                effective_from,
                effective_to,
                existing.effective_from,
                existing.effective_to,
            ):
                return True
        return False

    def to_dict(self):
        username = None
        display_name = None
        if self.user:
            username = self.user.username
            display_name = self.user.full_name or self.user.username
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "username": username,
            "user_display_name": display_name,
            "hourly_rate": float(self.hourly_rate) if self.hourly_rate is not None else None,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<RateOverride project={self.project_id} user={self.user_id} rate={self.hourly_rate}>"
