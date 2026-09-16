"""Geofence enforcement for workday clock-in/out."""

from typing import Any, Dict, List, Optional

from app.models.geofence import Geofence, GeofencePolicy
from app.models.workday_session import WorkdaySession
from app.services.gps_tracking_service import haversine_distance_m

_POLICY_RANK = {
    GeofencePolicy.LOG: 0,
    GeofencePolicy.WARN: 1,
    GeofencePolicy.BLOCK: 2,
}


class GeofenceService:
    """Check coordinates against configured geofences and enforce attendance policies."""

    def _applicable_geofences(self, session: Optional[WorkdaySession] = None) -> List[Geofence]:
        project_id = getattr(session, "project_id", None) if session else None
        return Geofence.active_query(project_id=project_id).all()

    def check_point(
        self,
        lat: float,
        lng: float,
        session: Optional[WorkdaySession] = None,
    ) -> Dict[str, Any]:
        """Return geofence match details for a coordinate pair."""
        geofences = self._applicable_geofences(session)
        if not geofences:
            return {
                "inside": True,
                "geofence_status": "no_geofences",
                "matches": [],
                "nearest": None,
            }

        matches = []
        nearest = None
        nearest_distance = None

        for geofence in geofences:
            distance_m = haversine_distance_m(lat, lng, geofence.lat, geofence.lng)
            inside = distance_m <= float(geofence.radius_m)
            entry = {
                "geofence": geofence,
                "geofence_id": geofence.id,
                "name": geofence.name,
                "distance_m": round(distance_m, 1),
                "radius_m": geofence.radius_m,
                "inside": inside,
                "policy": geofence.policy,
            }
            matches.append(entry)
            if nearest_distance is None or distance_m < nearest_distance:
                nearest_distance = distance_m
                nearest = entry
            if inside:
                return {
                    "inside": True,
                    "geofence_status": "inside",
                    "matches": matches,
                    "nearest": entry,
                    "geofence_id": geofence.id,
                    "geofence": geofence,
                    "distance_m": round(distance_m, 1),
                }

        return {
            "inside": False,
            "geofence_status": "outside",
            "matches": matches,
            "nearest": nearest,
            "geofence_id": None,
            "distance_m": round(nearest_distance, 1) if nearest_distance is not None else None,
        }

    def _strictest_policy(self, geofences: List[Geofence]) -> str:
        policy = GeofencePolicy.LOG
        for geofence in geofences:
            if _POLICY_RANK.get(geofence.policy, 0) > _POLICY_RANK.get(policy, 0):
                policy = geofence.policy
        return policy

    def _policy_to_action(self, policy: str) -> str:
        if policy == GeofencePolicy.BLOCK:
            return "block"
        if policy == GeofencePolicy.WARN:
            return "warn"
        return "allow"

    def _build_violation_message(self, check: Dict[str, Any]) -> str:
        nearest = check.get("nearest") or {}
        name = nearest.get("name") or "work area"
        distance_m = check.get("distance_m")
        if distance_m is not None:
            return f"You are {distance_m:.0f} m outside {name}."
        return f"You are outside the approved work area ({name})."

    def enforce_policy(
        self,
        user,
        lat: Optional[float],
        lng: Optional[float],
        session: Optional[WorkdaySession] = None,
    ) -> Dict[str, Any]:
        """Evaluate attendance policy for clock-in/out coordinates."""
        _ = user  # reserved for future per-user/project rules
        geofences = self._applicable_geofences(session)

        if not geofences:
            return {
                "action": "allow",
                "geofence_status": "no_geofences",
                "geofence_id": None,
                "distance_m": None,
                "message": None,
                "violation": None,
            }

        if lat is None or lng is None:
            policy = self._strictest_policy(geofences)
            action = self._policy_to_action(policy)
            message = "Location is required for geofenced attendance."
            result = {
                "action": action,
                "geofence_status": "unknown",
                "geofence_id": None,
                "distance_m": None,
                "message": message,
                "violation": {"reason": "missing_location", "policy": policy},
            }
            if action == "allow":
                result["message"] = None
            return result

        check = self.check_point(lat, lng, session=session)
        if check["inside"]:
            geofence = check.get("geofence")
            return {
                "action": "allow",
                "geofence_status": "inside",
                "geofence_id": check.get("geofence_id"),
                "distance_m": check.get("distance_m"),
                "message": None,
                "violation": None,
                "geofence_name": geofence.name if geofence else None,
            }

        policy = self._strictest_policy(geofences)
        action = self._policy_to_action(policy)
        message = self._build_violation_message(check)
        return {
            "action": action,
            "geofence_status": "outside",
            "geofence_id": None,
            "distance_m": check.get("distance_m"),
            "message": message,
            "violation": {
                "policy": policy,
                "nearest_geofence_id": (check.get("nearest") or {}).get("geofence_id"),
                "nearest_geofence_name": (check.get("nearest") or {}).get("name"),
                "distance_m": check.get("distance_m"),
            },
            "nearest_geofence": check.get("nearest"),
        }

    def apply_to_session(
        self,
        session: WorkdaySession,
        lat: Optional[float],
        lng: Optional[float],
        accuracy_m: Optional[float],
        enforcement: Dict[str, Any],
    ) -> None:
        """Persist geofence evaluation on a workday session."""
        session.latitude = lat
        session.longitude = lng
        session.accuracy_m = accuracy_m
        session.geofence_id = enforcement.get("geofence_id")
        session.geofence_status = enforcement.get("geofence_status")
