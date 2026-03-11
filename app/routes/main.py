from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app.models import User, Project, TimeEntry, Settings, WeeklyTimeGoal, TimeEntryTemplate, Activity, Client
from datetime import datetime, timedelta
from app import db, track_page_view
from sqlalchemy import text
from app.models.time_entry import local_now

from flask import make_response, current_app, session
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

    # Do not cache dashboard template_data: it contains ORM objects (active_timer,
    # recent_entries, top_projects, templates, etc.) that become detached when
    # served in a different request, causing "Instance not bound to a Session"
    # and "Database Error" on second visit (Issue #549).

    # Get user's active timer
    active_timer = current_user.active_timer

    # Get recent entries for the user (using repository to avoid N+1)
    from app.repositories import TimeEntryRepository

    time_entry_repo = TimeEntryRepository()
    recent_entries = time_entry_repo.get_by_user(user_id=current_user.id, limit=10, include_relations=True)

    # Get active projects and clients for timer dropdown (scoped for subcontractors)
    from app.utils.scope_filter import apply_project_scope_to_model, apply_client_scope_to_model

    projects_query = Project.query.filter_by(status="active").order_by(Project.name)
    scope_p = apply_project_scope_to_model(Project, current_user)
    if scope_p is not None:
        projects_query = projects_query.filter(scope_p)
    active_projects = projects_query.all()
    clients_query = Client.query.filter_by(status="active").order_by(Client.name)
    scope_c = apply_client_scope_to_model(Client, current_user)
    if scope_c is not None:
        clients_query = clients_query.filter(scope_c)
    active_clients = clients_query.all()
    only_one_client = len(active_clients) == 1
    single_client = active_clients[0] if only_one_client else None

    # Get user statistics and dashboard aggregations via analytics service
    from app.services import AnalyticsService
    from app.utils.overtime import calculate_period_overtime, get_week_start_for_date

    analytics_service = AnalyticsService()
    stats = analytics_service.get_dashboard_stats(user_id=current_user.id)
    today_hours = stats["time_tracking"]["today_hours"]
    week_hours = stats["time_tracking"]["week_hours"]
    month_hours = stats["time_tracking"]["month_hours"]

    # Overtime for dashboard cards (today and week)
    today_dt = datetime.utcnow().date()
    week_start_dt = get_week_start_for_date(today_dt, current_user)
    today_overtime = calculate_period_overtime(current_user, today_dt, today_dt)
    week_overtime = calculate_period_overtime(current_user, week_start_dt, today_dt)
    standard_hours_per_day = float(getattr(current_user, "standard_hours_per_day", 8.0) or 8.0)

    # Top projects (last 30 days) and time-by-project chart (last 7 days) from service
    top_projects = analytics_service.get_dashboard_top_projects(current_user.id, days=30, limit=5)
    chart_data = analytics_service.get_time_by_project_chart(current_user.id, days=7, limit=10)
    time_by_project_7d = chart_data["series"]
    chart_labels_7d = chart_data["chart_labels"]
    chart_hours_7d = chart_data["chart_hours"]

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

    # Recent tags for Start Timer modal autocomplete (distinct from user's time entries)
    recent_tags = []
    tag_rows = (
        db.session.query(TimeEntry.tags)
        .filter(
            TimeEntry.user_id == current_user.id,
            TimeEntry.tags.isnot(None),
            TimeEntry.tags != "",
        )
        .order_by(TimeEntry.updated_at.desc())
        .limit(200)
        .all()
    )
    tags_seen = set()
    for (tags_str,) in tag_rows:
        if tags_str:
            for part in tags_str.split(","):
                t = part.strip()
                if t and t not in tags_seen:
                    tags_seen.add(t)
                    recent_tags.append(t)
                    if len(recent_tags) >= 30:
                        break
        if len(recent_tags) >= 30:
            break

    # Last timer context: most recent completed time entry for "Repeat last" / quick start
    last_entry = (
        TimeEntry.query.filter(
            TimeEntry.user_id == current_user.id,
            TimeEntry.end_time.isnot(None),
        )
        .order_by(TimeEntry.end_time.desc())
        .limit(1)
        .first()
    )
    last_timer_context = None
    if last_entry and (last_entry.project_id or last_entry.client_id):
        last_timer_context = {
            "project_id": last_entry.project_id,
            "task_id": last_entry.task_id,
            "client_id": last_entry.client_id,
            "notes": (last_entry.notes or "").strip(),
            "tags": (last_entry.tags or "").strip(),
            "project_name": last_entry.project.name if last_entry.project else None,
            "client_name": last_entry.client.name if last_entry.client else None,
        }

    # Post-timer toast data (show "Logged Xh on Project" + link to time entries)
    timer_stopped_toast = session.pop("timer_stopped_toast", None)
    if timer_stopped_toast:
        timer_stopped_toast["time_entries_url"] = url_for("timer.time_entries_overview")

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
        "time_by_project_7d": time_by_project_7d,
        "chart_labels_7d": chart_labels_7d,
        "chart_hours_7d": chart_hours_7d,
        "current_week_goal": current_week_goal,
        "templates": templates,
        "recent_activities": recent_activities,
        "last_timer_context": last_timer_context,
        "recent_tags": recent_tags,
        "user_stats": user_stats,  # For smart banner
        "time_entries_count": time_entries_count,  # For donation widget
        "total_hours": total_hours,  # For donation widget
        "timer_stopped_toast": timer_stopped_toast,
    }

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
        variant = data.get("variant")

        # Get user metrics
        metrics = DonationInteraction.get_user_engagement_metrics(current_user.id)

        # Record click (variant for A/B segmentation)
        DonationInteraction.record_interaction(
            user_id=current_user.id,
            interaction_type="link_clicked",
            source=source,
            user_metrics=metrics,
            variant=variant,
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

        data = request.get_json() or {}
        variant = data.get("variant")

        # Get user metrics
        metrics = DonationInteraction.get_user_engagement_metrics(current_user.id)

        # Record dismissal (variant for A/B segmentation)
        DonationInteraction.record_interaction(
            user_id=current_user.id,
            interaction_type="banner_dismissed",
            source="banner",
            user_metrics=metrics,
            variant=variant,
        )

        return jsonify({"success": True})
    except Exception as e:
        # Return success even if tracking fails (e.g., table doesn't exist yet)
        return jsonify({"success": True, "note": "Tracking unavailable"})


@main_bp.route("/donate/track-impression", methods=["POST"])
@login_required
def track_support_impression():
    """Track support banner impression (banner_impression -> cta_click funnel)."""
    try:
        from app.models import DonationInteraction

        data = request.get_json() or {}
        source = data.get("source", "banner")
        variant = data.get("variant")

        metrics = DonationInteraction.get_user_engagement_metrics(current_user.id)
        DonationInteraction.record_interaction(
            user_id=current_user.id,
            interaction_type="banner_impression",
            source=source,
            user_metrics=metrics,
            variant=variant,
        )
        return jsonify({"success": True})
    except Exception:
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


@main_bp.route("/manifest.webmanifest")
def manifest():
    """Serve PWA manifest with theme_color. Prepared for custom themes - extend to use user accent preference when implemented."""
    theme_color = getattr(current_app.config, "PWA_THEME_COLOR", "#4A90E2")
    manifest_data = {
        "name": "TimeTracker - Professional Time Tracking",
        "short_name": "TimeTracker",
        "description": "Professional time tracking and project management application",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": theme_color,
        "orientation": "any",
        "icons": [
            {"src": url_for("static", filename="images/timetracker-logo.svg"), "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"},
            {"src": url_for("static", filename="images/android-chrome-192x192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": url_for("static", filename="images/android-chrome-512x512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            {"src": url_for("static", filename="images/apple-touch-icon.png"), "sizes": "180x180", "type": "image/png", "purpose": "any"},
        ],
        "screenshots": [],
        "categories": ["productivity", "business"],
        "shortcuts": [
            {"name": "Start Timer", "short_name": "Timer", "description": "Start tracking time", "url": url_for("timer.manual_entry"), "icons": [{"src": url_for("static", filename="images/timetracker-logo.svg"), "sizes": "96x96"}]},
            {"name": "Dashboard", "short_name": "Dashboard", "description": "View dashboard", "url": url_for("main.dashboard"), "icons": [{"src": url_for("static", filename="images/timetracker-logo.svg"), "sizes": "96x96"}]},
            {"name": "Projects", "short_name": "Projects", "description": "Manage projects", "url": url_for("projects.list_projects"), "icons": [{"src": url_for("static", filename="images/timetracker-logo.svg"), "sizes": "96x96"}]},
            {"name": "Reports", "short_name": "Reports", "description": "View reports", "url": url_for("reports.reports"), "icons": [{"src": url_for("static", filename="images/timetracker-logo.svg"), "sizes": "96x96"}]},
        ],
        "share_target": {"action": url_for("timer.manual_entry"), "method": "GET", "params": {"title": "notes", "text": "notes"}},
        "prefer_related_applications": False,
        "display_override": ["window-controls-overlay", "standalone"],
        "edge_side_panel": {"preferred_width": 400},
        "launch_handler": {"client_mode": "focus-existing"},
    }
    resp = make_response(json.dumps(manifest_data, indent=2))
    resp.headers["Content-Type"] = "application/manifest+json"
    return resp


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
