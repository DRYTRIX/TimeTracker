"""AI-powered project forecasting service.

Combines deterministic projections (velocity, burn rate, deadline risk) with an
optional LLM-generated narrative. All read-only — never raises, always returns
safe defaults so the forecast panel renders even with sparse or no data.
"""

from __future__ import annotations

import json
import logging
import math
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from app import db
from app.models import Project, Task, TimeEntry
from app.services.llm_service import AIServiceError, LLMService

logger = logging.getLogger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_percent(value: float) -> int:
    try:
        v = int(round(value))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, v))


class ForecastService:
    """Read-only project forecasting (deterministic math + optional AI narrative)."""

    # ------------------------------------------------------------- defaults

    @staticmethod
    def _empty_forecast(project: Optional[Project] = None) -> Dict[str, Any]:
        today = date.today()
        return {
            "has_data": False,
            # Velocity
            "total_logged_hours": 0.0,
            "days_with_entries": 0,
            "avg_hours_per_active_day": 0.0,
            "first_entry_date": None,
            "last_entry_date": None,
            "elapsed_calendar_days": 0,
            "avg_hours_per_calendar_day": 0.0,
            "velocity_hours_per_day": 0.0,
            # Budget
            "budget_hours": _safe_float(getattr(project, "estimated_hours", 0)) if project else 0.0,
            "budget_amount": (_safe_float(getattr(project, "budget_amount", 0)) if project else 0.0),
            "hourly_rate": (_safe_float(getattr(project, "hourly_rate", 0)) if project else 0.0),
            "hours_remaining": _safe_float(getattr(project, "estimated_hours", 0)) if project else 0.0,
            "budget_used_percent": 0,
            "budget_amount_used": 0.0,
            "budget_amount_remaining": (_safe_float(getattr(project, "budget_amount", 0)) if project else 0.0),
            "at_risk": False,
            # Timeline
            "days_to_completion": None,
            "projected_completion_date": None,
            "project_deadline": None,
            "days_until_deadline": None,
            "deadline_risk": "no_data",
            # Tasks
            "total_tasks": 0,
            "completed_tasks": 0,
            "open_tasks": 0,
            "task_completion_percent": 0,
            "overdue_tasks": 0,
            # Burn rate
            "recent_hours_7d": 0.0,
            "prior_hours_7d": 0.0,
            "burn_rate_trend": "stable",
            # Daily breakdown for chart
            "daily_hours": [],
            # Generated at (UTC ISO)
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "today": today.isoformat(),
        }

    # ----------------------------------------------------------- deterministic

    @classmethod
    def get_deterministic_forecast(cls, project_id: int, user=None) -> Dict[str, Any]:
        """Compute deterministic forecast metrics for a project.

        Never raises. Returns a flat dict with all forecast keys populated.
        """
        try:
            project = Project.query.get(int(project_id))
        except Exception:
            logger.exception("ForecastService: failed to load project %s", project_id)
            return cls._empty_forecast(None)

        if project is None:
            return cls._empty_forecast(None)

        forecast = cls._empty_forecast(project)
        today = date.today()

        # ---------------------------------------------- velocity / time entries
        try:
            rows = (
                db.session.query(TimeEntry.start_time, TimeEntry.duration_seconds)
                .filter(
                    TimeEntry.project_id == project.id,
                    TimeEntry.end_time.isnot(None),
                )
                .all()
            )
        except Exception:
            logger.exception("ForecastService: time entry query failed for project %s", project_id)
            rows = []

        total_seconds = 0
        by_day_seconds: Dict[date, int] = defaultdict(int)
        first_dt: Optional[datetime] = None
        last_dt: Optional[datetime] = None

        for start_time, duration_seconds in rows:
            sec = int(duration_seconds or 0)
            if sec <= 0:
                continue
            total_seconds += sec
            try:
                d = start_time.date() if hasattr(start_time, "date") else None
            except Exception:
                d = None
            if d is None:
                continue
            by_day_seconds[d] += sec
            if first_dt is None or start_time < first_dt:
                first_dt = start_time
            if last_dt is None or start_time > last_dt:
                last_dt = start_time

        total_logged_hours = round(total_seconds / 3600.0, 2)
        days_with_entries = len(by_day_seconds)
        avg_hours_per_active_day = round(total_logged_hours / days_with_entries, 2) if days_with_entries > 0 else 0.0

        first_entry_date = first_dt.date() if first_dt else None
        last_entry_date = last_dt.date() if last_dt else None

        if first_entry_date and last_entry_date and days_with_entries >= 2:
            elapsed_calendar_days = (last_entry_date - first_entry_date).days + 1
        elif days_with_entries == 1:
            elapsed_calendar_days = 1
        else:
            elapsed_calendar_days = 0

        avg_hours_per_calendar_day = (
            round(total_logged_hours / elapsed_calendar_days, 2) if elapsed_calendar_days > 0 else 0.0
        )

        # Velocity: avg_hours_per_calendar_day primary; if short history (< 7d),
        # also compute last-7-days velocity and use the higher (more conservative)
        # so we don't under-estimate completion time.
        velocity_hours_per_day = avg_hours_per_calendar_day
        if elapsed_calendar_days < 7 and total_logged_hours > 0:
            recent_window_start = today - timedelta(days=6)
            recent_seconds = sum(sec for d, sec in by_day_seconds.items() if d >= recent_window_start)
            recent_hours = recent_seconds / 3600.0
            recent_velocity = round(recent_hours / 7.0, 2)
            velocity_hours_per_day = max(velocity_hours_per_day, recent_velocity)

        forecast["total_logged_hours"] = total_logged_hours
        forecast["days_with_entries"] = int(days_with_entries)
        forecast["avg_hours_per_active_day"] = avg_hours_per_active_day
        forecast["first_entry_date"] = first_entry_date.isoformat() if first_entry_date else None
        forecast["last_entry_date"] = last_entry_date.isoformat() if last_entry_date else None
        forecast["elapsed_calendar_days"] = int(elapsed_calendar_days)
        forecast["avg_hours_per_calendar_day"] = avg_hours_per_calendar_day
        forecast["velocity_hours_per_day"] = float(velocity_hours_per_day)
        forecast["has_data"] = total_logged_hours > 0

        # --------------------------------------------------------- budget calc
        budget_hours = _safe_float(getattr(project, "estimated_hours", 0))
        budget_amount = _safe_float(getattr(project, "budget_amount", 0))
        hourly_rate = _safe_float(getattr(project, "hourly_rate", 0))
        if hourly_rate <= 0 and budget_hours > 0 and budget_amount > 0:
            try:
                hourly_rate = budget_amount / budget_hours
            except ZeroDivisionError:
                hourly_rate = 0.0

        hours_remaining = max(0.0, budget_hours - total_logged_hours)
        budget_used_percent = _clamp_percent((total_logged_hours / budget_hours) * 100) if budget_hours > 0 else 0
        budget_amount_used = round(total_logged_hours * hourly_rate, 2)
        budget_amount_remaining = max(0.0, budget_amount - budget_amount_used)
        at_risk = budget_used_percent >= 80 if budget_hours > 0 else False

        forecast["budget_hours"] = round(budget_hours, 2)
        forecast["budget_amount"] = round(budget_amount, 2)
        forecast["hourly_rate"] = round(hourly_rate, 2)
        forecast["hours_remaining"] = round(hours_remaining, 2)
        forecast["budget_used_percent"] = int(budget_used_percent)
        forecast["budget_amount_used"] = round(budget_amount_used, 2)
        forecast["budget_amount_remaining"] = round(budget_amount_remaining, 2)
        forecast["at_risk"] = bool(at_risk)

        # ------------------------------------------------------- timeline calc
        if velocity_hours_per_day > 0 and hours_remaining > 0:
            try:
                days_to_completion = int(math.ceil(hours_remaining / velocity_hours_per_day))
            except (ValueError, ZeroDivisionError):
                days_to_completion = None
            projected_completion_date = (
                today + timedelta(days=days_to_completion) if days_to_completion is not None else None
            )
        elif hours_remaining <= 0 and budget_hours > 0:
            days_to_completion = 0
            projected_completion_date = today
        else:
            days_to_completion = None
            projected_completion_date = None

        deadline_value = getattr(project, "deadline", None)
        project_deadline: Optional[date] = None
        if deadline_value is not None:
            try:
                project_deadline = deadline_value if isinstance(deadline_value, date) else deadline_value.date()
            except Exception:
                project_deadline = None

        days_until_deadline: Optional[int] = None
        if project_deadline is not None:
            days_until_deadline = (project_deadline - today).days

        deadline_risk = cls._compute_deadline_risk(velocity_hours_per_day, projected_completion_date, project_deadline)

        forecast["days_to_completion"] = days_to_completion
        forecast["projected_completion_date"] = (
            projected_completion_date.isoformat() if projected_completion_date else None
        )
        forecast["project_deadline"] = project_deadline.isoformat() if project_deadline else None
        forecast["days_until_deadline"] = days_until_deadline
        forecast["deadline_risk"] = deadline_risk

        # ------------------------------------------------------------ tasks
        try:
            task_rows = db.session.query(Task.status, Task.due_date).filter(Task.project_id == project.id).all()
        except Exception:
            logger.exception("ForecastService: task query failed for project %s", project_id)
            task_rows = []

        total_tasks = len(task_rows)
        completed_tasks = sum(1 for status, _due in task_rows if status == "done")
        open_tasks = sum(1 for status, _due in task_rows if status not in ("done", "cancelled"))
        overdue_tasks = sum(
            1 for status, due in task_rows if due is not None and due < today and status not in ("done", "cancelled")
        )
        task_completion_percent = _clamp_percent((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

        forecast["total_tasks"] = int(total_tasks)
        forecast["completed_tasks"] = int(completed_tasks)
        forecast["open_tasks"] = int(open_tasks)
        forecast["task_completion_percent"] = int(task_completion_percent)
        forecast["overdue_tasks"] = int(overdue_tasks)

        # ------------------------------------------------------- burn rate 7/7
        last_7_start = today - timedelta(days=6)
        prior_7_start = today - timedelta(days=13)
        prior_7_end = today - timedelta(days=7)
        recent_seconds = sum(sec for d, sec in by_day_seconds.items() if d >= last_7_start)
        prior_seconds = sum(sec for d, sec in by_day_seconds.items() if prior_7_start <= d <= prior_7_end)
        recent_hours_7d = round(recent_seconds / 3600.0, 2)
        prior_hours_7d = round(prior_seconds / 3600.0, 2)

        if prior_hours_7d <= 0 and recent_hours_7d <= 0:
            burn_rate_trend = "stable"
        elif prior_hours_7d <= 0 and recent_hours_7d > 0:
            burn_rate_trend = "increasing"
        elif recent_hours_7d > prior_hours_7d * 1.1:
            burn_rate_trend = "increasing"
        elif recent_hours_7d < prior_hours_7d * 0.9:
            burn_rate_trend = "decreasing"
        else:
            burn_rate_trend = "stable"

        forecast["recent_hours_7d"] = recent_hours_7d
        forecast["prior_hours_7d"] = prior_hours_7d
        forecast["burn_rate_trend"] = burn_rate_trend

        # ----------------------------------------- daily breakdown for chart
        daily_hours: List[Dict[str, Any]] = []
        chart_start = today - timedelta(days=13)
        cur = chart_start
        while cur <= today:
            daily_hours.append(
                {
                    "date": cur.isoformat(),
                    "hours": round(by_day_seconds.get(cur, 0) / 3600.0, 2),
                }
            )
            cur += timedelta(days=1)
        forecast["daily_hours"] = daily_hours

        return forecast

    @staticmethod
    def _compute_deadline_risk(velocity: float, projected_completion: Optional[date], deadline: Optional[date]) -> str:
        """Map (velocity, projected completion, deadline) to a coarse risk label."""
        if velocity is None or velocity <= 0 or projected_completion is None:
            return "no_data"
        if deadline is None:
            return "on_track"
        try:
            delta_days = (projected_completion - deadline).days
        except Exception:
            return "no_data"
        if delta_days <= 0:
            return "on_track"
        if delta_days <= 7:
            return "at_risk"
        return "overdue"

    # ------------------------------------------------------------ AI narrative

    @classmethod
    def get_ai_forecast(cls, project_id: int, user) -> Dict[str, Any]:
        """Run deterministic forecast and ask the LLM for a short narrative.

        Returns a dict with keys: ok, narrative, risks, recommendations, deterministic.
        On any failure (LLM disabled, bad JSON, provider error) returns ok=False
        with a populated error string and empty risk/recommendation lists, while
        still including the deterministic forecast so the caller can render it.
        """
        deterministic = cls.get_deterministic_forecast(project_id, user=user)

        try:
            project = Project.query.get(int(project_id))
        except Exception:
            project = None
        if project is None:
            return {
                "ok": False,
                "error": "Project not found",
                "error_code": "not_found",
                "narrative": None,
                "risks": [],
                "recommendations": [],
                "deterministic": deterministic,
            }

        service = LLMService()
        try:
            service.ensure_enabled()
        except AIServiceError as exc:
            return {
                "ok": False,
                "error": exc.message,
                "error_code": exc.code,
                "narrative": None,
                "risks": [],
                "recommendations": [],
                "deterministic": deterministic,
            }

        context = {
            "project": {
                "name": project.name,
                "status": project.status,
                "estimated_hours": project.estimated_hours,
                "budget_amount": (float(project.budget_amount) if project.budget_amount is not None else None),
                "deadline": (
                    getattr(project, "deadline", None).isoformat() if getattr(project, "deadline", None) else None
                ),
            },
            "forecast": deterministic,
            "today": date.today().isoformat(),
        }

        prompt = (
            "You are a project management assistant. Based on the following project "
            "data and forecast, provide:\n"
            "1. A 2-sentence executive summary of the project's health\n"
            "2. Up to 3 specific risks (as a JSON array of short strings)\n"
            "3. Up to 3 actionable recommendations (as a JSON array of short strings)\n\n"
            "Respond ONLY with valid JSON in this exact shape:\n"
            "{\n"
            '  "narrative": "...",\n'
            '  "risks": ["...", "..."],\n'
            '  "recommendations": ["...", "..."]\n'
            "}\n\n"
            "Project data:\n" + json.dumps(context, default=str, ensure_ascii=False)
        )

        try:
            response = service._chat_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a project forecasting assistant. " "Respond only with the requested JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=400,
            )
        except AIServiceError as exc:
            return {
                "ok": False,
                "error": exc.message,
                "error_code": exc.code,
                "narrative": None,
                "risks": [],
                "recommendations": [],
                "deterministic": deterministic,
            }
        except Exception as exc:
            logger.exception("ForecastService: AI completion failed for project %s", project_id)
            return {
                "ok": False,
                "error": str(exc) or "ai_error",
                "error_code": "ai_error",
                "narrative": None,
                "risks": [],
                "recommendations": [],
                "deterministic": deterministic,
            }

        raw_content = (response or {}).get("content") or ""
        parsed = cls._parse_ai_json(raw_content)
        if parsed is None:
            return {
                "ok": False,
                "error": "Could not parse AI response",
                "error_code": "ai_parse_error",
                "narrative": None,
                "risks": [],
                "recommendations": [],
                "deterministic": deterministic,
            }

        narrative = parsed.get("narrative")
        risks = parsed.get("risks") or []
        recommendations = parsed.get("recommendations") or []

        return {
            "ok": True,
            "narrative": str(narrative).strip() if narrative else "",
            "risks": [str(r).strip() for r in risks if isinstance(r, (str, int, float))][:3],
            "recommendations": [str(r).strip() for r in recommendations if isinstance(r, (str, int, float))][:3],
            "deterministic": deterministic,
        }

    @staticmethod
    def _parse_ai_json(content: str) -> Optional[Dict[str, Any]]:
        """Strip ```json fences and parse the model's JSON response."""
        if not content:
            return None
        text = content.strip()
        # Strip ```json ... ``` fences, including bare ``` fences.
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if fence_match:
            text = fence_match.group(1)
        else:
            # Try to find the first JSON object in the text.
            obj_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if obj_match:
                text = obj_match.group(0)
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        return data
