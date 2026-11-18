"""Admin UI routes for reminder policies (Phase 4 – invoicing gaps)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app import db
from app.models.reminder_policy import ReminderPolicy, ReminderPolicyLevel
from app.utils.permissions import admin_or_permission_required

reminder_policies_bp = Blueprint("reminder_policies", __name__)


@reminder_policies_bp.route("/admin/reminder-policies")
@login_required
@admin_or_permission_required("access_admin")
def list_policies():
    policies = ReminderPolicy.query.order_by(ReminderPolicy.is_default.desc(), ReminderPolicy.name).all()
    return render_template("reminder_policies/list.html", policies=policies)


@reminder_policies_bp.route("/admin/reminder-policies/create", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("access_admin")
def create_policy():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Policy name is required.", "error")
            return redirect(url_for("reminder_policies.create_policy"))

        is_default = bool(request.form.get("is_default"))
        if is_default:
            # Unset any existing default
            ReminderPolicy.query.filter_by(is_default=True).update({"is_default": False})

        policy = ReminderPolicy(name=name, is_default=is_default)
        db.session.add(policy)
        db.session.flush()  # get policy.id

        _save_levels(policy, request.form)
        db.session.commit()
        flash(f"Reminder policy '{name}' created.", "success")
        return redirect(url_for("reminder_policies.list_policies"))

    return render_template("reminder_policies/edit.html", policy=None)


@reminder_policies_bp.route("/admin/reminder-policies/<int:policy_id>/edit", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("access_admin")
def edit_policy(policy_id):
    policy = ReminderPolicy.query.get_or_404(policy_id)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Policy name is required.", "error")
            return redirect(url_for("reminder_policies.edit_policy", policy_id=policy_id))

        is_default = bool(request.form.get("is_default"))
        if is_default and not policy.is_default:
            ReminderPolicy.query.filter_by(is_default=True).update({"is_default": False})

        policy.name = name
        policy.active = bool(request.form.get("active"))
        policy.is_default = is_default

        # Replace all levels
        for lv in policy.levels.all():
            db.session.delete(lv)
        db.session.flush()

        _save_levels(policy, request.form)
        db.session.commit()
        flash(f"Reminder policy '{name}' updated.", "success")
        return redirect(url_for("reminder_policies.list_policies"))

    return render_template("reminder_policies/edit.html", policy=policy)


@reminder_policies_bp.route("/admin/reminder-policies/<int:policy_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("access_admin")
def delete_policy(policy_id):
    policy = ReminderPolicy.query.get_or_404(policy_id)
    db.session.delete(policy)
    db.session.commit()
    flash(f"Reminder policy '{policy.name}' deleted.", "success")
    return redirect(url_for("reminder_policies.list_policies"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _save_levels(policy: ReminderPolicy, form) -> None:
    """Parse multi-level form data and add ReminderPolicyLevel rows."""
    # Levels are submitted as:
    #   level_days_offset[]  level_template_name[]  level_late_fee_type[]
    #   level_late_fee_value[]  level_sort_order[]  level_active[]
    offsets = form.getlist("level_days_offset[]")
    templates = form.getlist("level_template_name[]")
    fee_types = form.getlist("level_late_fee_type[]")
    fee_values = form.getlist("level_late_fee_value[]")
    sort_orders = form.getlist("level_sort_order[]")
    actives = form.getlist("level_active[]")

    for idx, offset_str in enumerate(offsets):
        offset_str = offset_str.strip()
        if not offset_str:
            continue
        try:
            days_offset = int(offset_str)
        except ValueError:
            continue

        fee_type = fee_types[idx].strip() if idx < len(fee_types) else ""
        fee_value_str = fee_values[idx].strip() if idx < len(fee_values) else ""
        sort_order_str = sort_orders[idx].strip() if idx < len(sort_orders) else "0"
        active_val = actives[idx] if idx < len(actives) else "0"

        from decimal import Decimal, InvalidOperation

        try:
            fee_value = Decimal(fee_value_str) if fee_value_str else None
        except InvalidOperation:
            fee_value = None

        try:
            sort_order = int(sort_order_str)
        except ValueError:
            sort_order = idx

        lv = ReminderPolicyLevel(
            policy_id=policy.id,
            days_offset=days_offset,
            template_name=templates[idx].strip() if idx < len(templates) else None,
            late_fee_type=fee_type or None,
            late_fee_value=fee_value,
            sort_order=sort_order,
            active=bool(active_val and active_val != "0"),
        )
        db.session.add(lv)
