"""Admin pages of the Legal entities module: our billing entities and their payment accounts."""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db, log_event
from app.models import BillingEntity, PaymentAccount
from app.utils.db import safe_commit
from app.utils.module_helpers import module_enabled
from app.utils.permissions import admin_or_permission_required

billing_entities_bp = Blueprint("billing_entities", __name__)

VAT_CATEGORIES = ("S", "Z", "E", "AE", "K", "G", "O", "L", "M")


def _clean(name, limit=None):
    value = (request.form.get(name, "") or "").strip()
    if limit:
        value = value[:limit]
    return value or None


def _entities():
    return BillingEntity.query.order_by(BillingEntity.status, BillingEntity.short_name).all()


def _fill_entity(entity):
    entity.short_name = _clean("short_name", 200) or entity.short_name
    entity.legal_name = _clean("legal_name", 255) or entity.short_name
    country = (_clean("country", 2) or "").upper()
    entity.country = country or None
    entity.registration_number = _clean("registration_number", 100)
    entity.vat_number = _clean("vat_number", 100)
    entity.address = _clean("address")
    entity.email = _clean("email", 200)
    entity.phone = _clean("phone", 50)
    entity.website = _clean("website", 200)
    entity.number_format = _clean("number_format", 120)
    vat = (_clean("default_vat_category", 5) or "").upper()
    entity.default_vat_category = vat if vat in VAT_CATEGORIES else None
    rate = _clean("default_tax_rate")
    try:
        entity.default_tax_rate = Decimal(rate) if rate else None
    except InvalidOperation:
        entity.default_tax_rate = None
    entity.default_vat_exemption_code = _clean("default_vat_exemption_code", 50)
    entity.default_vat_exemption_reason = _clean("default_vat_exemption_reason")
    entity.default_terms = _clean("default_terms")
    entity.default_notes = _clean("default_notes")


@billing_entities_bp.route("/admin/legal-entities")
@billing_entities_bp.route("/admin/legal-entities/<int:entity_id>")
@login_required
@module_enabled("billing_entities")
@admin_or_permission_required("manage_settings")
def index(entity_id=None):
    entities = _entities()
    entity = None
    if entity_id:
        entity = BillingEntity.query.get_or_404(entity_id)
    elif entities:
        entity = entities[0]
    return render_template(
        "billing_entities/index.html",
        entities=entities,
        entity=entity,
        vat_categories=VAT_CATEGORIES,
    )


@billing_entities_bp.route("/admin/legal-entities/new", methods=["GET", "POST"])
@login_required
@module_enabled("billing_entities")
@admin_or_permission_required("manage_settings")
def create():
    if request.method == "GET":
        return _render_new(None)
    short_name = _clean("short_name", 200)
    entity = BillingEntity(short_name=short_name, legal_name=short_name)
    _fill_entity(entity)
    if not short_name:
        flash(_("Short name is required"), "error")
        return _render_new(entity), 400
    db.session.add(entity)
    if not safe_commit("billing_entity_create", {"short_name": short_name}):
        flash(_("Could not save the legal entity"), "error")
        return _render_new(entity), 400
    log_event("billing_entity.created", user_id=current_user.id, billing_entity_id=entity.id)
    # Step 2: the entity's first payment account, with a "created" banner and a Skip link
    return redirect(url_for("billing_entities.new_account", entity_id=entity.id, created=1))


def _render_new(entity):
    """The Add entity page; ``entity`` is an unsaved one holding the typed values after an error."""
    return render_template("billing_entities/new.html", entity=entity, vat_categories=VAT_CATEGORIES)


@billing_entities_bp.route("/admin/legal-entities/<int:entity_id>", methods=["POST"])
@login_required
@module_enabled("billing_entities")
@admin_or_permission_required("manage_settings")
def update(entity_id):
    entity = BillingEntity.query.get_or_404(entity_id)
    _fill_entity(entity)
    if not safe_commit("billing_entity_update", {"billing_entity_id": entity.id}):
        flash(_("Could not save the legal entity"), "error")
    else:
        flash(_("Legal entity saved"), "success")
    return redirect(url_for("billing_entities.index", entity_id=entity.id))


@billing_entities_bp.route("/admin/legal-entities/<int:entity_id>/archive", methods=["POST"])
@login_required
@module_enabled("billing_entities")
@admin_or_permission_required("manage_settings")
def toggle_archive(entity_id):
    entity = BillingEntity.query.get_or_404(entity_id)
    entity.status = "active" if entity.status == "archived" else "archived"
    safe_commit("billing_entity_archive", {"billing_entity_id": entity.id})
    flash(_("Legal entity archived") if entity.status == "archived" else _("Legal entity restored"), "success")
    return redirect(url_for("billing_entities.index", entity_id=entity.id))


@billing_entities_bp.route("/admin/legal-entities/<int:entity_id>/delete", methods=["POST"])
@login_required
@module_enabled("billing_entities")
@admin_or_permission_required("manage_settings")
def delete(entity_id):
    entity = BillingEntity.query.get_or_404(entity_id)
    if entity.is_used():
        flash(_("Used on invoices, archive it instead"), "error")
        return redirect(url_for("billing_entities.index", entity_id=entity.id))
    db.session.delete(entity)
    safe_commit("billing_entity_delete", {"billing_entity_id": entity_id})
    flash(_("Legal entity deleted"), "success")
    return redirect(url_for("billing_entities.index"))


# --- Payment accounts ---------------------------------------------------------------------------


def _account_or_404(entity, account_id):
    account = PaymentAccount.query.get_or_404(account_id)
    if account.billing_entity_id != entity.id:
        abort(404)
    return account


def _render_account(entity, account, form=None):
    return render_template(
        "billing_entities/account.html",
        entity=entity,
        account=account,
        form=form or {},
        created=request.args.get("created") == "1",
    )


def _save_account(entity, account):
    currency = (_clean("currency", 3) or "").upper()
    iban = (_clean("iban", 64) or "").replace(" ", "").upper()
    if len(currency) != 3 or not iban:
        flash(_("Currency and IBAN are required"), "error")
        return None
    duplicate = PaymentAccount.query.filter_by(iban=iban, currency=currency).first()
    if duplicate and (account is None or duplicate.id != account.id):
        flash(_("An account with this IBAN and currency already exists"), "error")
        return None
    if account is None:
        account = PaymentAccount(billing_entity_id=entity.id, currency=currency, iban=iban)
        db.session.add(account)
    account.currency = currency
    account.iban = iban
    account.bank_name = _clean("bank_name", 120)
    status = request.form.get("status", "active")
    account.status = status if status in ("active", "archived") else "active"

    account.details_text = (request.form.get("details_text") or "").strip() or None
    return account


@billing_entities_bp.route("/admin/legal-entities/<int:entity_id>/accounts/new", methods=["GET", "POST"])
@login_required
@module_enabled("billing_entities")
@admin_or_permission_required("manage_settings")
def new_account(entity_id):
    entity = BillingEntity.query.get_or_404(entity_id)
    if request.method == "GET":
        return _render_account(entity, None)
    account = _save_account(entity, None)
    if account is None or not safe_commit("payment_account_create", {"billing_entity_id": entity.id}):
        db.session.rollback()
        return _render_account(entity, None, form=request.form), 400
    flash(_("Payment account created"), "success")
    if request.form.get("next") == "another":
        return redirect(url_for("billing_entities.new_account", entity_id=entity.id))
    return redirect(url_for("billing_entities.index", entity_id=entity.id))


@billing_entities_bp.route("/admin/legal-entities/<int:entity_id>/accounts/<int:account_id>", methods=["GET", "POST"])
@login_required
@module_enabled("billing_entities")
@admin_or_permission_required("manage_settings")
def account(entity_id, account_id):
    entity = BillingEntity.query.get_or_404(entity_id)
    account = _account_or_404(entity, account_id)
    if request.method == "GET":
        return _render_account(entity, account)
    if _save_account(entity, account) is None or not safe_commit(
        "payment_account_update", {"payment_account_id": account.id}
    ):
        db.session.rollback()
        return redirect(url_for("billing_entities.account", entity_id=entity.id, account_id=account.id))
    flash(_("Payment account saved"), "success")
    return redirect(url_for("billing_entities.index", entity_id=entity.id))


@billing_entities_bp.route("/admin/legal-entities/<int:entity_id>/accounts/<int:account_id>/archive", methods=["POST"])
@login_required
@module_enabled("billing_entities")
@admin_or_permission_required("manage_settings")
def archive_account(entity_id, account_id):
    entity = BillingEntity.query.get_or_404(entity_id)
    account = _account_or_404(entity, account_id)
    account.status = "active" if account.status == "archived" else "archived"
    safe_commit("payment_account_archive", {"payment_account_id": account.id})
    flash(_("Payment account archived") if account.status == "archived" else _("Payment account restored"), "success")
    return redirect(url_for("billing_entities.index", entity_id=entity.id))


@billing_entities_bp.route("/admin/legal-entities/<int:entity_id>/accounts/<int:account_id>/delete", methods=["POST"])
@login_required
@module_enabled("billing_entities")
@admin_or_permission_required("manage_settings")
def delete_account(entity_id, account_id):
    entity = BillingEntity.query.get_or_404(entity_id)
    account = _account_or_404(entity, account_id)
    if account.is_used():
        flash(_("Used on an invoice, archive it instead"), "error")
        return redirect(url_for("billing_entities.account", entity_id=entity.id, account_id=account.id))
    db.session.delete(account)
    safe_commit("payment_account_delete", {"payment_account_id": account_id})
    flash(_("Payment account deleted"), "success")
    return redirect(url_for("billing_entities.index", entity_id=entity.id))
