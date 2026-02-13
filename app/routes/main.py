from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app.models import User, Project, TimeEntry, Settings, WeeklyTimeGoal, TimeEntryTemplate, Activity
from datetime import datetime, timedelta
from app import db, track_page_view
from sqlalchemy import text
from app.models.time_entry import local_now

from flask import make_response, current_app
import json
import os
from app.utils.posthog_segmentation import update_user_segments_if_needed

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard showing active timer and recent entries - REFACTORED to use services and fix N+1 queries"""
    # Track dashboard page view
    track_page_view("dashboard")

    # Update user segments periodically (cached, not every request)
    update_user_segments_if_needed(current_user.id, current_user)

    # Use caching for dashboard data (5 minute TTL)
    # Skip cache when testing: cached data can contain ORM objects that become detached
    # when served in a different request, causing "Instance not bound to a Session" errors.
    from app.utils.cache import get_cache, cached

    cache = get_cache()
    cache_key = f"dashboard:{current_user.id}"
    use_cache = not current_app.testing

    if use_cache:
        cached_data = cache.get(cache_key)
        if cached_data:
            return render_template("main/dashboard.html", **cached_data)

    # Get user's active timer
    active_timer = current_user.active_timer

    # Get recent entries for the user (using repository to avoid N+1)
    from app.repositories import TimeEntryRepository

    time_entry_repo = TimeEntryRepository()
    recent_entries = time_entry_repo.get_by_user(user_id=current_user.id, limit=10, include_relations=True)

    # Get active projects for timer dropdown (using repository)
    from app.repositories import ProjectRepository, ClientRepository

    project_repo = ProjectRepository()
    client_repo = ClientRepository()
    active_projects = project_repo.get_active_projects()
    active_clients = client_repo.get_active_clients()
    only_one_client = len(active_clients) == 1
    single_client = active_clients[0] if only_one_client else None

    # Get user statistics using analytics service
    from app.services import AnalyticsService

    analytics_service = AnalyticsService()
    stats = analytics_service.get_dashboard_stats(user_id=current_user.id)

    today_hours = stats["time_tracking"]["today_hours"]
    week_hours = stats["time_tracking"]["week_hours"]
    month_hours = stats["time_tracking"]["month_hours"]

    # Overtime for dashboard cards (today and week)
    from app.utils.overtime import calculate_period_overtime
    today_dt = datetime.utcnow().date()
    week_start_dt = today_dt - timedelta(days=today_dt.weekday())
    today_overtime = calculate_period_overtime(current_user, today_dt, today_dt)
    week_overtime = calculate_period_overtime(current_user, week_start_dt, today_dt)
    standard_hours_per_day = float(getattr(current_user, "standard_hours_per_day", 8.0) or 8.0)

    # Build Top Projects (last 30 days) - using optimized query with eager loading
    from sqlalchemy.orm import joinedload

    period_start = datetime.utcnow().date() - timedelta(days=30)
    entries_30 = (
        TimeEntry.query.options(joinedload(TimeEntry.project))  # Eager load projects to avoid N+1
        .filter(
            TimeEntry.end_time.isnot(None), TimeEntry.start_time >= period_start, TimeEntry.user_id == current_user.id
        )
        .all()
    )
    project_hours = {}
    for e in entries_30:
        if not e.project:
            continue
        project_hours.setdefault(e.project.id, {"project": e.project, "hours": 0.0, "billable_hours": 0.0})
        project_hours[e.project.id]["hours"] += e.duration_hours
        if e.billable and e.project.billable:
            project_hours[e.project.id]["billable_hours"] += e.duration_hours
    top_projects = sorted(project_hours.values(), key=lambda x: x["hours"], reverse=True)[:5]

    # Get current week goal
    current_week_goal = WeeklyTimeGoal.get_current_week_goal(current_user.id)
    if current_week_goal:
        current_week_goal.update_status()

    # Get user's time entry templates (most recently used first)
    from sqlalchemy import desc
    from sqlalchemy.orm import joinedload

    templates = (
        TimeEntryTemplate.query.options(joinedload(TimeEntryTemplate.project), joinedload(TimeEntryTemplate.task))
        .filter_by(user_id=current_user.id)
        .order_by(desc(TimeEntryTemplate.last_used_at))
        .limit(5)
        .all()
    )

    # Get recent activities for activity feed widget
    recent_activities = Activity.get_recent(user_id=None if current_user.is_admin else current_user.id, limit=10)

    # Get user stats for smart banner and donation widget
    try:
        from app.models import DonationInteraction
        user_stats = DonationInteraction.get_user_engagement_metrics(current_user.id)
    except Exception:
        # Fallback if table doesn't exist yet
        days_since_signup = (datetime.utcnow() - current_user.created_at).days if current_user.created_at else 0
        time_entries_count = TimeEntry.query.filter_by(user_id=current_user.id).count()
        total_hours = current_user.total_hours if hasattr(current_user, "total_hours") else 0.0
        user_stats = {
            "days_since_signup": days_since_signup,
            "time_entries_count": time_entries_count,
            "total_hours": total_hours,
        }
    
    # Get donation widget stats (separate from user_stats for clarity)
    time_entries_count = user_stats.get("time_entries_count", 0)
    total_hours = user_stats.get("total_hours", 0.0)
    
    # Prepare template data
    template_data = {
        "active_timer": active_timer,
        "recent_entries": recent_entries,
        "active_projects": active_projects,
        "active_clients": active_clients,
        "only_one_client": only_one_client,
        "single_client": single_client,
        "today_hours": today_hours,
        "week_hours": week_hours,
        "month_hours": month_hours,
        "standard_hours_per_day": standard_hours_per_day,
        "today_regular_hours": today_overtime["regular_hours"],
        "today_overtime_hours": today_overtime["overtime_hours"],
        "week_regular_hours": week_overtime["regular_hours"],
        "week_overtime_hours": week_overtime["overtime_hours"],
        "top_projects": top_projects,
        "current_week_goal": current_week_goal,
        "templates": templates,
        "recent_activities": recent_activities,
        "user_stats": user_stats,  # For smart banner
        "time_entries_count": time_entries_count,  # For donation widget
        "total_hours": total_hours,  # For donation widget
    }

    if use_cache:
        cache.set(cache_key, template_data, ttl=300)

    return render_template("main/dashboard.html", **template_data)


@main_bp.route("/_health")
def health_check():
    """Liveness probe: shallow checks only, no DB access"""
    return {"status": "healthy"}, 200


@main_bp.route("/_ready")
def readiness_check():
    """Readiness probe: verify DB connectivity and critical dependencies"""
    try:
        db.session.execute(text("SELECT 1"))
        return {"status": "ready", "timestamp": local_now().isoformat()}, 200
    except Exception as e:
        return {"status": "not_ready", "error": "db_unreachable"}, 503


@main_bp.route("/about")
def about():
    """About page"""
    return render_template("main/about.html")


@main_bp.route("/help")
def help():
    """Help page"""
    return render_template("main/help.html")


@main_bp.route("/donate")
@login_required
def donate():
    """Donation page explaining why donations are important"""
    from app.models import TimeEntry
    
    # Get user engagement metrics
    days_since_signup = (datetime.utcnow() - current_user.created_at).days if current_user.created_at else 0
    time_entries_count = TimeEntry.query.filter_by(user_id=current_user.id).count()
    total_hours = current_user.total_hours if hasattr(current_user, "total_hours") else 0.0
    
    # Record page view (only if table exists)
    try:
        from app.models import DonationInteraction
        DonationInteraction.record_interaction(
            user_id=current_user.id,
            interaction_type="page_viewed",
            source="donate_page",
            user_metrics={
                "days_since_signup": days_since_signup,
                "time_entries_count": time_entries_count,
                "total_hours": total_hours,
            }
        )
    except Exception:
        # Don't fail if tracking fails (e.g., table doesn't exist yet)
        pass
    
    return render_template(
        "main/donate.html",
        days_since_signup=days_since_signup,
        time_entries_count=time_entries_count,
        total_hours=total_hours,
    )


@main_bp.route("/donate/track-click", methods=["POST"])
@login_required
def track_donation_click():
    """Track donation link clicks"""
    try:
        from app.models import DonationInteraction
        
        data = request.get_json() or {}
        source = data.get("source", "unknown")
        
        # Get user metrics
        metrics = DonationInteraction.get_user_engagement_metrics(current_user.id)
        
        # Record click
        DonationInteraction.record_interaction(
            user_id=current_user.id,
            interaction_type="link_clicked",
            source=source,
            user_metrics=metrics,
        )
        
        return jsonify({"success": True})
    except Exception as e:
        # Return success even if tracking fails (e.g., table doesn't exist yet)
        return jsonify({"success": True, "note": "Tracking unavailable"})


@main_bp.route("/donate/track-banner-dismissal", methods=["POST"])
@login_required
def track_banner_dismissal():
    """Track banner dismissals"""
    try:
        from app.models import DonationInteraction
        
        # Get user metrics
        metrics = DonationInteraction.get_user_engagement_metrics(current_user.id)
        
        # Record dismissal
        DonationInteraction.record_interaction(
            user_id=current_user.id,
            interaction_type="banner_dismissed",
            source="banner",
            user_metrics=metrics,
        )
        
        return jsonify({"success": True})
    except Exception as e:
        # Return success even if tracking fails (e.g., table doesn't exist yet)
        return jsonify({"success": True, "note": "Tracking unavailable"})


@main_bp.route("/debug/i18n")
@login_required
def debug_i18n():
    """Debug endpoint to check i18n status (admin only)"""
    from flask_login import current_user

    if not current_user.is_admin:
        return jsonify({"error": "Admin only"}), 403

    from flask_babel import get_locale
    import os

    locale = str(get_locale())
    session_lang = session.get("preferred_language")
    user_lang = getattr(current_user, "preferred_language", None)

    # Check if .mo file exists for current locale
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    translations_dir = os.path.join(base_path, "translations")
    mo_path = os.path.join(translations_dir, locale, "LC_MESSAGES", "messages.mo")
    po_path = os.path.join(translations_dir, locale, "LC_MESSAGES", "messages.po")

    return jsonify(
        {
            "current_locale": locale,
            "session_language": session_lang,
            "user_language": user_lang,
            "mo_file_exists": os.path.exists(mo_path),
            "po_file_exists": os.path.exists(po_path),
            "mo_path": mo_path,
            "nb_mo_exists": os.path.exists(os.path.join(translations_dir, "nb", "LC_MESSAGES", "messages.mo")),
            "no_mo_exists": os.path.exists(os.path.join(translations_dir, "no", "LC_MESSAGES", "messages.mo")),
        }
    )


@main_bp.route("/i18n/set-language", methods=["POST", "GET"])
def set_language():
    """Set preferred UI language via session or user profile."""
    lang = (
        request.args.get("lang")
        or (request.form.get("lang") if request.method == "POST" else None)
        or (request.json.get("lang") if request.is_json else None)
        or "en"
    )
    lang = lang.strip().lower()
    from flask import current_app

    supported = list(current_app.config.get("LANGUAGES", {}).keys()) or ["en"]
    if lang not in supported:
        lang = current_app.config.get("BABEL_DEFAULT_LOCALE", "en")

    # Make session permanent to ensure it persists across requests
    session.permanent = True

    # Persist in session for guests
    session["preferred_language"] = lang
    session.modified = True  # Force session save

    # If authenticated, persist to user profile
    try:
        from flask_login import current_user

        if current_user and getattr(current_user, "is_authenticated", False):
            # Update user preference in database
            current_user.preferred_language = lang
            # Add to session and commit
            db.session.add(current_user)
            db.session.commit()
            # Expire all cached objects to ensure fresh load on next request
            db.session.expire_all()
    except Exception as e:
        # If database save fails, rollback but continue with session
        try:
            db.session.rollback()
        except Exception:
            pass

    # Redirect back if referer exists, add timestamp to force reload
    next_url = request.headers.get("Referer") or url_for("main.dashboard")
    # Add cache-busting parameter to ensure fresh page load
    import time

    separator = "&" if "?" in next_url else "?"
    next_url = f"{next_url}{separator}_lang_refresh={int(time.time())}"
    response = make_response(redirect(next_url))
    # Ensure no caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@main_bp.route("/search")
@login_required
def search():
    """Search time entries"""
    query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    if not query:
        return redirect(url_for("main.dashboard"))

    # Search in time entries
    from sqlalchemy import or_

    entries = (
        TimeEntry.query.filter(
            TimeEntry.user_id == current_user.id,
            TimeEntry.end_time.isnot(None),
            or_(TimeEntry.notes.ilike(f"%{query}%"), TimeEntry.tags.ilike(f"%{query}%")),
        )
        .order_by(TimeEntry.start_time.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )

    return render_template("main/search.html", entries=entries, query=query)


@main_bp.route("/service-worker.js")
def service_worker():
    """Serve a minimal service worker for PWA offline caching."""
    # Build absolute URLs for static assets to ensure proper caching
    assets = [
        "/",
        # CSS
        url_for("static", filename="dist/output.css"),
        url_for("static", filename="enhanced-ui.css"),
        url_for("static", filename="ui-enhancements.css"),
        url_for("static", filename="form-validation.css"),
        url_for("static", filename="keyboard-shortcuts.css"),
        url_for("static", filename="toast-notifications.css"),
        # JS
        url_for("static", filename="mobile.js"),
        url_for("static", filename="commands.js"),
        url_for("static", filename="enhanced-ui.js"),
        url_for("static", filename="ui-enhancements.js"),
        url_for("static", filename="toast-notifications.js"),
    ]
    preamble = "const CACHE_NAME='tt-cache-v2';\n"
    assets_js = "const ASSETS=" + json.dumps(assets) + ";\n\n"
    body = "self.addEventListener('install', (event)=>{ event.waitUntil(caches.open(CACHE_NAME).then((c)=>c.addAll(ASSETS))); self.skipWaiting()); });\n".replace(
        "); );", ");"
    )  # guard against formatting
    body = (
        "self.addEventListener('install', (event)=>{\n"
        "  event.waitUntil((async()=>{\n"
        "    const cache = await caches.open(CACHE_NAME);\n"
        "    try { await cache.addAll(ASSETS); } catch(e) {}\n"
        "    self.skipWaiting();\n"
        "  })());\n"
        "});\n"
        "self.addEventListener('activate', (event)=>{\n"
        "  event.waitUntil((async()=>{\n"
        "    const keys = await caches.keys();\n"
        "    await Promise.all(keys.map((k)=>{ if(k!==CACHE_NAME){ return caches.delete(k); } return null; }));\n"
        "    self.clients.claim();\n"
        "  })());\n"
        "});\n"
        "self.addEventListener('fetch', (event)=>{\n"
        "  const req = event.request;\n"
        "  if (req.method !== 'GET') { return; }\n"
        "  const url = new URL(req.url);\n"
        "  const sameOrigin = url.origin === self.location.origin;\n"
        "  if (!sameOrigin) {\n"
        "    // Do not intercept cross-origin (CDN) requests\n"
        "    return;\n"
        "  }\n"
        "  event.respondWith((async()=>{\n"
        "    const cached = await caches.match(req);\n"
        "    if (cached) return cached;\n"
        "    try {\n"
        "      const res = await fetch(req);\n"
        "      const cache = await caches.open(CACHE_NAME);\n"
        "      cache.put(req, res.clone());\n"
        "      return res;\n"
        "    } catch(e) {\n"
        "      const fallback = await caches.match('/');\n"
        "      return fallback || new Response('', { status: 504, statusText: 'Gateway Timeout' });\n"
        "    }\n"
        "  })());\n"
        "});\n"
    )
    sw_js = preamble + assets_js + body
    resp = make_response(sw_js)
    resp.headers["Content-Type"] = "application/javascript"
    return resp
