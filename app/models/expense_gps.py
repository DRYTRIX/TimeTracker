"""
GPS tracking models for mileage expenses
"""

from datetime import datetime
from typing import Optional
from app import db
from sqlalchemy import Index


class MileageTrack(db.Model):
    """GPS track for mileage expense calculation"""

    __tablename__ = "mileage_tracks"

    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expenses.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Track metadata
    start_location = db.Column(db.String(200), nullable=True)  # Address or coordinates
    end_location = db.Column(db.String(200), nullable=True)
    start_latitude = db.Column(db.Numeric(10, 8), nullable=True)
    start_longitude = db.Column(db.Numeric(11, 8), nullable=True)
    end_latitude = db.Column(db.Numeric(10, 8), nullable=True)
    end_longitude = db.Column(db.Numeric(11, 8), nullable=True)

    # Calculated distance
    distance_km = db.Column(db.Numeric(10, 2), nullable=True)
    distance_miles = db.Column(db.Numeric(10, 2), nullable=True)

    # Track points (JSON array of {lat, lng, timestamp})
    track_points = db.Column(db.JSON, nullable=True)

    # Timing
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)

    # Metadata
    method = db.Column(db.String(50), default="gps", nullable=False)  # 'gps', 'manual', 'route_calculation'
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    expense = db.relationship("Expense", backref=db.backref("gps_tracks", lazy="dynamic"))
    user = db.relationship("User", backref=db.backref("mileage_tracks", lazy="dynamic"))

    __table_args__ = (Index("ix_mileage_tracks_user_started", "user_id", "started_at"),)

    def __repr__(self):
        return f"<MileageTrack {self.id} - {self.distance_km}km>"

    def to_dict(self):
        return {
            "id": self.id,
            "expense_id": self.expense_id,
            "user_id": self.user_id,
            "start_location": self.start_location,
            "end_location": self.end_location,
            "start_latitude": float(self.start_latitude) if self.start_latitude else None,
            "start_longitude": float(self.start_longitude) if self.start_longitude else None,
            "end_latitude": float(self.end_latitude) if self.end_latitude else None,
            "end_longitude": float(self.end_longitude) if self.end_longitude else None,
            "distance_km": float(self.distance_km) if self.distance_km else None,
            "distance_miles": float(self.distance_miles) if self.distance_miles else None,
            "track_points": self.track_points,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_seconds": self.duration_seconds,
            "method": self.method,
            "notes": self.notes,
        }

    def calculate_distance(self):
        """Calculate distance from GPS coordinates using Haversine formula"""
        if not all([self.start_latitude, self.start_longitude, self.end_latitude, self.end_longitude]):
            return None

        from math import radians, sin, cos, sqrt, atan2

        # Haversine formula
        R = 6371  # Earth radius in km

        lat1 = radians(float(self.start_latitude))
        lon1 = radians(float(self.start_longitude))
        lat2 = radians(float(self.end_latitude))
        lon2 = radians(float(self.end_longitude))

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance_km = R * c
        distance_miles = distance_km * 0.621371

        self.distance_km = distance_km
        self.distance_miles = distance_miles

        return distance_km

    def calculate_distance_from_track_points(self) -> Optional[float]:
        """Calculate total distance from track points"""
        if not self.track_points or len(self.track_points) < 2:
            return None

        from math import radians, sin, cos, sqrt, atan2

        R = 6371  # Earth radius in km
        total_distance = 0.0

        for i in range(len(self.track_points) - 1):
            point1 = self.track_points[i]
            point2 = self.track_points[i + 1]

            lat1 = radians(float(point1.get("lat", 0)))
            lon1 = radians(float(point1.get("lng", 0)))
            lat2 = radians(float(point2.get("lat", 0)))
            lon2 = radians(float(point2.get("lng", 0)))

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))

            segment_distance = R * c
            total_distance += segment_distance

        self.distance_km = total_distance
        self.distance_miles = total_distance * 0.621371

        return total_distance
