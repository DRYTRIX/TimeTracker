from datetime import date, datetime, timedelta

from flask import Blueprint, flash, render_template, request
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db
from app.models import Task, TimeEntry, User

resource_scheduling_bp = Blueprint("resource_scheduling", __name__)


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


@resource_scheduling_bp.route("/team/schedule")
@login_required
def team_schedule():
    week_of_str = request.args.get("week_of", "").strip()
    try:
        week_of = datetime.strptime(week_of_str, "%Y-%m-%d").date() if week_of_str else date.today()
    except ValueError:
        week_of = date.today()
        flash(_("Invalid week date; showing this week."), "warning")
    start = _week_start(week_of)
    days = [start + timedelta(days=i) for i in range(7)]
    end = days[-1]

    user_ids = request.args.getlist("user_id", type=int)
    users_query = User.query.filter_by(is_active=True).order_by(User.username)
    if user_ids:
        users_query = users_query.filter(User.id.in_(user_ids))
    elif not (current_user.is_admin or current_user.has_permission("view_all_time_entries")):
        users_query = users_query.filter(User.id == current_user.id)
    users = users_query.all()

    tasks = (
        Task.query.filter(Task.assigned_to.in_([u.id for u in users]) if users else False, Task.due_date.between(start, end))
        .all()
        if users
        else []
    )
    tasks_by_user_day = {}
    for task in tasks:
        tasks_by_user_day.setdefault((task.assigned_to, task.due_date), []).append(task)

    actuals = {}
    if users:
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())
        rows = (
            db.session.query(
                TimeEntry.user_id,
                TimeEntry.start_time,
                TimeEntry.duration_seconds,
            )
            .filter(
                TimeEntry.user_id.in_([u.id for u in users]),
                TimeEntry.end_time.isnot(None),
                TimeEntry.start_time >= start_dt,
                TimeEntry.start_time <= end_dt,
            )
            .all()
        )
        for user_id, start_time, seconds in rows:
            day = start_time.date() if start_time else None
            if day:
                actuals[(user_id, day)] = actuals.get((user_id, day), 0) + (seconds or 0)

    lanes = []
    for user in users:
        daily_cap = float(user.daily_hour_limit_override or user.standard_hours_per_day or 8)
        cells = []
        for day in days:
            day_tasks = tasks_by_user_day.get((user.id, day), [])
            planned = sum(float(t.estimated_hours or 0) for t in day_tasks)
            actual_hours = round(actuals.get((user.id, day), 0) / 3600, 2)
            cells.append(
                {
                    "date": day,
                    "tasks": day_tasks,
                    "planned_hours": planned,
                    "actual_hours": actual_hours,
                    "capacity": daily_cap,
                    "over_capacity": planned > daily_cap,
                }
            )
        lanes.append({"user": user, "cells": cells})

    prev_week = start - timedelta(days=7)
    next_week = start + timedelta(days=7)
    all_users = User.query.filter_by(is_active=True).order_by(User.username).all()
    return render_template(
        "team/schedule.html",
        lanes=lanes,
        days=days,
        week_start=start,
        prev_week=prev_week,
        next_week=next_week,
        users=all_users,
        selected_user_ids=user_ids,
    )
