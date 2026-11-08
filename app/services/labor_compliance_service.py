"""Labor-compliance export presets (Belgium attendance, EU WTD, US FLSA)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.models import Settings, TimeEntry, User

# Preset registry: id → metadata + default weekly hour threshold
PRESETS: Dict[str, Dict[str, Any]] = {
    "belgium-attendance": {
        "id": "belgium-attendance",
        "name": "Belgium attendance (inspector)",
        "description": "Daily attendance periods, breaks, rest, and overtime for Belgian labor inspection.",
        "kind": "attendance",
        "default_weekly_threshold": None,
        "settings_key": None,
    },
    "eu-wtd": {
        "id": "eu-wtd",
        "name": "EU Working Time Directive",
        "description": "Weekly hours vs EU WTD threshold (default 48h); flags weeks over the limit.",
        "kind": "weekly_hours",
        "default_weekly_threshold": 48.0,
        "settings_key": "weekly_hour_limit",
    },
    "us-flsa": {
        "id": "us-flsa",
        "name": "US FLSA overtime",
        "description": "Weekly hours with FLSA overtime (>40h/week by default).",
        "kind": "weekly_hours",
        "default_weekly_threshold": 40.0,
        "settings_key": "compliance_standard_weekly_hours",
    },
}


class LaborComplianceService:
    """Build labor-compliance export rows from named presets."""

    def list_presets(self) -> List[Dict[str, Any]]:
        return [dict(p) for p in PRESETS.values()]

    def get_preset(self, preset_id: str) -> Optional[Dict[str, Any]]:
        return PRESETS.get((preset_id or "").strip().lower())

    def resolve_weekly_threshold(
        self,
        preset_id: str,
        *,
        weekly_threshold: Optional[float] = None,
    ) -> Optional[float]:
        preset = self.get_preset(preset_id)
        if not preset or preset.get("kind") != "weekly_hours":
            return None
        if weekly_threshold is not None:
            try:
                return float(weekly_threshold)
            except (TypeError, ValueError):
                pass
        settings = Settings.get_settings()
        key = preset.get("settings_key")
        if key and hasattr(settings, key):
            val = getattr(settings, key, None)
            if val is not None:
                try:
                    return float(val)
                except (TypeError, ValueError):
                    pass
        return float(preset.get("default_weekly_threshold") or 40.0)

    def export_rows(
        self,
        preset_id: str,
        *,
        start_date: date,
        end_date: date,
        user_id: Optional[int] = None,
        weekly_threshold: Optional[float] = None,
        overages_only: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Return (rows, meta). Raises ValueError for unknown preset."""
        preset = self.get_preset(preset_id)
        if not preset:
            raise ValueError(f"Unknown labor-compliance preset: {preset_id}")

        meta: Dict[str, Any] = {
            "preset_id": preset["id"],
            "preset_name": preset["name"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        if preset["kind"] == "attendance":
            from app.services.attendance_compliance_service import AttendanceComplianceService

            rows = AttendanceComplianceService().belgium_inspector_rows(
                start_date=start_date, end_date=end_date, user_id=user_id
            )
            return rows, meta

        threshold = self.resolve_weekly_threshold(preset_id, weekly_threshold=weekly_threshold)
        meta["weekly_threshold"] = threshold
        rows = self._weekly_hours_rows(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            weekly_threshold=float(threshold or 40.0),
            earning_label="OT" if preset_id == "us-flsa" else "OVER_LIMIT",
            overages_only=overages_only,
        )
        return rows, meta

    def _weekly_hours_rows(
        self,
        *,
        start_date: date,
        end_date: date,
        user_id: Optional[int],
        weekly_threshold: float,
        earning_label: str,
        overages_only: bool,
    ) -> List[Dict[str, Any]]:
        query = TimeEntry.query.filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= datetime.combine(start_date, datetime.min.time()),
            TimeEntry.start_time <= datetime.combine(end_date, datetime.max.time()),
        )
        if user_id is not None:
            query = query.filter(TimeEntry.user_id == user_id)

        buckets: Dict[tuple, Dict[str, Any]] = {}
        for entry in query.all():
            entry_date = entry.start_time.date()
            iso_year, iso_week, _ = entry_date.isocalendar()
            week_start = date.fromisocalendar(iso_year, iso_week, 1)
            week_end = week_start + timedelta(days=6)
            key = (entry.user_id, iso_year, iso_week)
            if key not in buckets:
                user = entry.user or User.query.get(entry.user_id)
                buckets[key] = {
                    "user_id": entry.user_id,
                    "username": user.username if user else "",
                    "display_name": getattr(user, "display_name", None) or (user.username if user else ""),
                    "week_year": iso_year,
                    "week_number": iso_week,
                    "week_start": week_start.isoformat(),
                    "week_end": week_end.isoformat(),
                    "total_hours": 0.0,
                    "weekly_threshold": weekly_threshold,
                    "overtime_hours": 0.0,
                    "over_limit": "no",
                    "earning_code": "REG",
                }
            hours = float(entry.duration_seconds or 0) / 3600.0
            buckets[key]["total_hours"] += hours

        rows: List[Dict[str, Any]] = []
        for item in buckets.values():
            total = round(item["total_hours"], 2)
            overtime = round(max(0.0, total - weekly_threshold), 2)
            item["total_hours"] = total
            item["overtime_hours"] = overtime
            item["regular_hours"] = round(min(total, weekly_threshold), 2)
            item["over_limit"] = "yes" if overtime > 0 else "no"
            item["earning_code"] = earning_label if overtime > 0 else "REG"
            if overages_only and overtime <= 0:
                continue
            rows.append(item)

        rows.sort(key=lambda r: (r["week_year"], r["week_number"], r["user_id"] or 0))
        return rows
