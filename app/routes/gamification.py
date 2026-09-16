"""Gamification routes — badges, leaderboards, and admin CRUD."""

from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db
from app.models.gamification import Badge, Leaderboard, LeaderboardEntry, UserBadge
from app.services.gamification_service import GamificationService
from app.utils.db import safe_commit
from app.utils.permissions import admin_or_permission_required

gamification_bp = Blueprint("gamification", __name__)


def ensure_default_gamification_data():
    """Seed default badges and weekly hours leaderboard if empty."""
    if Badge.query.count() == 0:
        defaults = [
            ("First Entry", "Log your first time entry", "fa-play", "milestone", {"type": "milestone", "milestone_type": "first_time_entry"}, 10, "common"),
            ("10 Hours Tracked", "Track 10 billable hours", "fa-clock", "achievement", {"type": "time_tracked", "target_hours": 10}, 25, "common"),
            ("100 Hours Tracked", "Track 100 billable hours", "fa-trophy", "achievement", {"type": "time_tracked", "target_hours": 100}, 100, "rare"),
            ("7-Day Streak", "Log time 7 days in a row", "fa-fire", "streak", {"type": "streak", "target_days": 7}, 50, "rare"),
            ("First Task", "Complete your first task", "fa-check", "milestone", {"type": "milestone", "milestone_type": "first_task"}, 15, "common"),
            ("First Invoice", "Create your first invoice", "fa-file-invoice", "milestone", {"type": "milestone", "milestone_type": "first_invoice"}, 20, "common"),
            ("Task Master", "Complete 25 tasks", "fa-tasks", "achievement", {"type": "tasks_completed", "target_count": 25}, 75, "epic"),
            ("Project Closer", "Complete a project", "fa-flag-checkered", "achievement", {"type": "projects_completed", "target_count": 1}, 40, "rare"),
        ]
        for name, desc, icon, btype, criteria, points, rarity in defaults:
            db.session.add(
                Badge(
                    name=name,
                    description=desc,
                    icon=icon,
                    badge_type=btype,
                    criteria=criteria,
                    points=points,
                    rarity=rarity,
                    is_active=True,
                )
            )
    if Leaderboard.query.filter_by(name="Weekly Hours").count() == 0:
        db.session.add(
            Leaderboard(
                name="Weekly Hours",
                description="Hours tracked this week",
                leaderboard_type="time_tracked",
                period="weekly",
                scope="global",
                is_active=True,
            )
        )
    safe_commit("seed_gamification")


@gamification_bp.route("/gamification/leaderboard")
@login_required
def leaderboard_page():
    ensure_default_gamification_data()
    svc = GamificationService()
    boards = Leaderboard.query.filter_by(is_active=True).order_by(Leaderboard.name.asc()).all()
    board_id = request.args.get("board_id", type=int)
    board = Leaderboard.query.get(board_id) if board_id else (boards[0] if boards else None)
    entries = []
    if board:
        try:
            svc.calculate_leaderboard(board.id)
        except Exception:
            pass
        entries = svc.get_leaderboard(board.id, limit=50)
    my_badges = svc.get_user_badges(current_user.id)
    my_points = svc.get_user_points(current_user.id)
    return render_template(
        "gamification/leaderboard.html",
        boards=boards,
        board=board,
        entries=entries,
        my_badges=my_badges,
        my_points=my_points,
    )


@gamification_bp.route("/api/v1/gamification/me")
@login_required
def api_me():
    svc = GamificationService()
    return jsonify(
        {
            "badges": svc.get_user_badges(current_user.id),
            "points": svc.get_user_points(current_user.id),
        }
    )


@gamification_bp.route("/api/v1/gamification/badges")
@login_required
def api_badges():
    ensure_default_gamification_data()
    badges = Badge.query.filter_by(is_active=True).order_by(Badge.points.asc()).all()
    return jsonify({"badges": [b.to_dict() for b in badges]})


@gamification_bp.route("/api/v1/gamification/leaderboard")
@login_required
def api_leaderboard():
    ensure_default_gamification_data()
    board = Leaderboard.query.filter_by(is_active=True).first()
    if not board:
        return jsonify({"entries": []})
    svc = GamificationService()
    try:
        svc.calculate_leaderboard(board.id)
    except Exception:
        pass
    return jsonify({"leaderboard": board.to_dict(), "entries": svc.get_leaderboard(board.id, limit=50)})


@gamification_bp.route("/admin/gamification", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("access_admin")
def admin_gamification():
    ensure_default_gamification_data()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "badge":
            badge = Badge(
                name=(request.form.get("name") or "").strip(),
                description=(request.form.get("description") or "").strip() or None,
                icon=(request.form.get("icon") or "fa-medal").strip(),
                badge_type=(request.form.get("badge_type") or "achievement").strip(),
                criteria={"type": request.form.get("criteria_type") or "time_tracked", "target_hours": request.form.get("target", type=int) or 10},
                points=request.form.get("points", type=int) or 10,
                rarity=(request.form.get("rarity") or "common").strip(),
                is_active=True,
            )
            if badge.name:
                db.session.add(badge)
                safe_commit("create_badge")
                flash(_("Badge created"), "success")
        elif action == "leaderboard":
            board = Leaderboard(
                name=(request.form.get("name") or "").strip(),
                description=(request.form.get("description") or "").strip() or None,
                leaderboard_type=(request.form.get("leaderboard_type") or "time_tracked").strip(),
                period=(request.form.get("period") or "weekly").strip(),
                scope="global",
                is_active=True,
            )
            if board.name:
                db.session.add(board)
                safe_commit("create_leaderboard")
                flash(_("Leaderboard created"), "success")
        return redirect(url_for("gamification.admin_gamification"))

    badges = Badge.query.order_by(Badge.name.asc()).all()
    boards = Leaderboard.query.order_by(Leaderboard.name.asc()).all()
    return render_template("admin/gamification.html", badges=badges, boards=boards)
