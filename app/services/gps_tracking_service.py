"""
GPS Tracking Service for mileage expenses
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from app import db
from app.models.expense_gps import MileageTrack
from app.models import Expense
import logging

logger = logging.getLogger(__name__)


class GPSTrackingService:
    """Service for GPS tracking and mileage calculation"""

    def start_tracking(
        self, user_id: int, latitude: float = None, longitude: float = None, location: str = None
    ) -> Dict[str, Any]:
        """Start GPS tracking for mileage"""
        track = MileageTrack(
            user_id=user_id, start_latitude=latitude, start_longitude=longitude, start_location=location, method="gps"
        )

        db.session.add(track)
        db.session.commit()

        return {"success": True, "track_id": track.id, "track": track.to_dict()}

    def add_track_point(
        self, track_id: int, latitude: float, longitude: float, timestamp: datetime = None
    ) -> Dict[str, Any]:
        """Add a GPS point to the track"""
        track = MileageTrack.query.get_or_404(track_id)

        if not track.track_points:
            track.track_points = []

        point = {"lat": latitude, "lng": longitude, "timestamp": (timestamp or datetime.utcnow()).isoformat()}

        track.track_points.append(point)
        track.updated_at = datetime.utcnow()

        db.session.commit()

        return {"success": True, "track": track.to_dict()}

    def stop_tracking(
        self, track_id: int, latitude: float = None, longitude: float = None, location: str = None
    ) -> Dict[str, Any]:
        """Stop GPS tracking and calculate distance"""
        track = MileageTrack.query.get_or_404(track_id)

        if track.ended_at:
            return {"success": False, "message": "Tracking already stopped"}

        track.end_latitude = latitude
        track.end_longitude = longitude
        track.end_location = location
        track.ended_at = datetime.utcnow()
        track.duration_seconds = int((track.ended_at - track.started_at).total_seconds())

        # Calculate distance
        if track.track_points and len(track.track_points) > 1:
            # Use track points for more accurate distance
            distance = track.calculate_distance_from_track_points()
        elif track.start_latitude and track.end_latitude:
            # Use start/end coordinates
            distance = track.calculate_distance()
        else:
            distance = None

        db.session.commit()

        return {
            "success": True,
            "track": track.to_dict(),
            "distance_km": float(distance) if distance else None,
            "distance_miles": float(track.distance_miles) if track.distance_miles else None,
        }

    def create_expense_from_track(
        self, track_id: int, project_id: int = None, rate_per_km: float = None
    ) -> Dict[str, Any]:
        """Create expense from GPS track"""
        track = MileageTrack.query.get_or_404(track_id)

        if not track.ended_at:
            return {"success": False, "message": "Tracking must be stopped before creating expense"}

        if not track.distance_km:
            return {"success": False, "message": "Distance not calculated"}

        # Calculate amount
        rate = rate_per_km or 0.5  # Default rate
        amount = float(track.distance_km) * rate

        # Create expense
        expense = Expense(
            user_id=track.user_id,
            project_id=project_id,
            date=track.started_at.date(),
            amount=amount,
            category="mileage",
            description=f"Mileage: {track.start_location or 'Start'} to {track.end_location or 'End'}",
            notes=f"GPS tracked: {track.distance_km}km ({track.distance_miles} miles)",
        )

        db.session.add(expense)
        db.session.flush()

        # Link track to expense
        track.expense_id = expense.id
        db.session.commit()

        return {"success": True, "expense": expense.to_dict(), "track": track.to_dict()}

    def calculate_route_distance(
        self, start_lat: float, start_lng: float, end_lat: float, end_lng: float
    ) -> Dict[str, Any]:
        """Calculate route distance between two points (can use routing API)"""
        # Simple Haversine calculation (straight line)
        # In production, use Google Maps API or similar for actual route distance

        from math import radians, sin, cos, sqrt, atan2

        R = 6371  # Earth radius in km

        lat1 = radians(start_lat)
        lon1 = radians(start_lng)
        lat2 = radians(end_lat)
        lon2 = radians(end_lng)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance_km = R * c
        distance_miles = distance_km * 0.621371

        return {
            "distance_km": round(distance_km, 2),
            "distance_miles": round(distance_miles, 2),
            "method": "haversine",  # Straight line, not actual route
        }

    def get_user_tracks(
        self, user_id: int, start_date: datetime = None, end_date: datetime = None, limit: int = 50
    ) -> List[Dict]:
        """Get GPS tracks for a user"""
        query = MileageTrack.query.filter_by(user_id=user_id)

        if start_date:
            query = query.filter(MileageTrack.started_at >= start_date)
        if end_date:
            query = query.filter(MileageTrack.started_at <= end_date)

        tracks = query.order_by(MileageTrack.started_at.desc()).limit(limit).all()

        return [t.to_dict() for t in tracks]
