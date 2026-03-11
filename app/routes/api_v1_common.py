"""
Shared helpers for API v1 routes.
Used by api_v1.py and by domain-specific sub-blueprints (e.g. api_v1_time_entries).
"""

from flask import request, jsonify, g


def paginate_query(query, page=None, per_page=None):
    """Paginate a SQLAlchemy query."""
    page = page or int(request.args.get("page", 1))
    per_page = per_page or int(request.args.get("per_page", 50))
    per_page = min(per_page, 100)

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        "items": paginated.items,
        "pagination": {
            "page": paginated.page,
            "per_page": paginated.per_page,
            "total": paginated.total,
            "pages": paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
            "next_page": paginated.page + 1 if paginated.has_next else None,
            "prev_page": paginated.page - 1 if paginated.has_prev else None,
        },
    }


def parse_datetime(dt_str):
    """Parse datetime string from API request."""
    if not dt_str:
        return None
    try:
        from app.utils.timezone import utc_to_local

        ts = dt_str.strip()
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        from datetime import datetime

        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is not None:
            dt = utc_to_local(dt).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _parse_date(dstr):
    """Parse a YYYY-MM-DD string to date."""
    if not dstr:
        return None
    try:
        from datetime import date as _date

        return _date.fromisoformat(str(dstr))
    except Exception:
        return None


def _parse_date_range(start_date_str, end_date_str):
    """Parse start/end date params. Date-only end_date becomes end-of-day."""
    start_dt = parse_datetime(start_date_str) if start_date_str else None
    end_dt = parse_datetime(end_date_str) if end_date_str else None

    if end_date_str and end_dt and "T" not in end_date_str.strip() and " " not in end_date_str.strip():
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    return start_dt, end_dt


def _require_module_enabled_for_api(module_id: str):
    """Return a Flask response tuple if module is disabled for this API user; otherwise None."""
    try:
        from app.models import Settings
        from app.utils.module_registry import ModuleRegistry

        settings = Settings.get_settings()
        user = getattr(g, "api_user", None)
        if not ModuleRegistry.is_enabled(module_id, settings, user):
            return (
                jsonify(
                    {
                        "error": "module_disabled",
                        "message": f"{module_id} module is disabled by the administrator.",
                    }
                ),
                403,
            )
    except Exception:
        pass
    return None
