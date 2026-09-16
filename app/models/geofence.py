"""Geofence definitions for field attendance policies."""

from datetime import datetime

from app import db


class GeofencePolicy:
    LOG = "log"
    WARN = "warn"
    BLOCK = "block"

    CHOICES = (LOG, WARN, BLOCK)


class Geofence(db.Model):
    __tablename__ = "geofences"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    radius_m = db.Column(db.Float, nullable=False, default=100.0)
    address = db.Column(db.String(500), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    policy = db.Column(db.String(10), nullable=False, default=GeofencePolicy.LOG)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = db.relationship("Project", backref=db.backref("geofences", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "radius_m": self.radius_m,
            "address": self.address,
            "project_id": self.project_id,
            "project_name": self.project.name if self.project else None,
            "is_active": self.is_active,
            "policy": self.policy,
        }

    @classmethod
    def active_query(cls, project_id=None):
        """Active geofences applicable to a workday context."""
        query = cls.query.filter_by(is_active=True)
        if project_id is None:
            query = query.filter(cls.project_id.is_(None))
        else:
            query = query.filter(db.or_(cls.project_id.is_(None), cls.project_id == project_id))
        return query.order_by(cls.name.asc())
