"""Admin → Invoice templates: HTML invoice templates next to the stock layout designer.

The page is a library. Which template invoices print with is set in Settings (default for
all) and, with the legal-entities module, on each legal entity. See
``app/utils/invoice_templates.py``.
"""

from __future__ import annotations

import io
import re
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required
from markupsafe import Markup

from app import db, limiter
from app.models import Invoice, InvoiceHtmlTemplate, Settings
from app.utils.db import safe_commit
from app.utils.invoice_pdf_html import (  # noqa: F401  (asset routes)
    MAX_TEMPLATE_BYTES,
    TEMPLATE_VARIABLES,
    TemplateError,
    _logo_path,
    available_fonts,
    font_files,
    html_to_pdf,
    render_invoice_html,
    validate_template,
)
from app.utils.invoice_templates import (
    BUILTIN_DESCRIPTIONS,
    builtin_names,
    builtin_source,
    default_template_ref,
    entities_with_own_template,
    on_template_deleted,
    ref_label,
    template_choices,
    used_by,
    uses_visual_layout,
)
from app.utils.permissions import admin_or_permission_required

invoice_templates_bp = Blueprint("invoice_templates", __name__)

PREVIEW_INVOICES = 20
SAMPLE = "sample"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _settings():
    return Settings.get_settings()


def _preview_settings(invoice):
    """Settings the PDF generator would use for this invoice (its legal entity, when there is one)."""
    settings = _settings()
    try:
        from app.utils.billing_entities import seller_settings_for  # legal-entities module, when installed

        return seller_settings_for(invoice, settings)
    except ImportError:
        return settings


def sample_invoice():
    """An invoice that lives only in memory: for previews when there are no invoices yet."""
    lines = [
        ("Development\n\nFor period 01.12.2026-31.12.2026", "96", "70.00"),
        ("Code review", "24.5", "45.00"),
        ("Project management", "8", "60.00"),
    ] * 8
    items = [
        SimpleNamespace(
            id=i,
            position=i,
            description=d,
            quantity=Decimal(q),
            unit_price=Decimal(r),
            total_amount=Decimal(q) * Decimal(r),
        )
        for i, (d, q, r) in enumerate(lines)
    ]
    subtotal = sum(i.total_amount for i in items)
    tax = (subtotal * Decimal("0.20")).quantize(Decimal("0.01"))
    today = date.today()
    client = SimpleNamespace(name="Sample Client Ltd", vat_id="GB123456789", address=None, email=None, custom_fields={})
    return SimpleNamespace(
        id=None,
        invoice_number="SAMPLE-0001",
        issue_date=today,
        due_date=today + timedelta(days=30),
        status="draft",
        client=client,
        client_name="Sample Client Ltd",
        client_address="1 Example Street\nLondon EC1A 1AA",
        client_email="accounts@client.example",
        items=items,
        extra_goods=[],
        expenses=[],
        subtotal=subtotal,
        tax_rate=Decimal("20"),
        tax_amount=tax,
        discount_amount=Decimal("0"),
        total_amount=subtotal + tax,
        currency_code=getattr(_settings(), "currency", None) or "EUR",
        notes="Services under the agreement of 1 January 2026",
        terms="Payment within 30 days.",
    )


def _preview_invoice(value):
    """The invoice to preview on: an id from the select, or the sample."""
    if value and str(value) != SAMPLE:
        try:
            invoice = db.session.get(Invoice, int(value))
        except (TypeError, ValueError):
            invoice = None
        if invoice is not None:
            return invoice
    return sample_invoice()


def _preview_choices():
    invoices = Invoice.query.order_by(Invoice.id.desc()).limit(PREVIEW_INVOICES).all()
    choices = [
        (
            str(i.id),
            f"{i.invoice_number} · {i.client_name} · {i.issue_date.strftime('%d/%m/%Y') if i.issue_date else ''}"
            f" · {i.currency_code} {i.total_amount}",
        )
        for i in invoices
    ]
    choices.append((SAMPLE, _("Sample invoice (hourly, 24 lines)")))
    return choices


_PAGE_MARGIN_RE = re.compile(r"@page\s*\{[^}]*?\bmargin\s*:\s*([^;}]+)", re.IGNORECASE | re.DOTALL)


def _with_asset_base(html: str) -> str:
    """For the browser preview: fonts/… and logo resolve against our asset routes, and the
    page margins from ``@page`` (which browsers ignore on screen) become body padding."""
    base = Markup('<base href="{}">').format(url_for("invoice_templates.asset", path=""))
    margin = _PAGE_MARGIN_RE.search(html)
    if margin and re.fullmatch(r"[\d.\s]+(mm|cm|in|pt|px)?(\s+[\d.]+(mm|cm|in|pt|px)?){0,3}", margin.group(1).strip()):
        base += Markup(
            "<style>@media screen {{ html {{ background: #fff; }} body {{ padding: {}; }} }}</style>"
        ).format(margin.group(1).strip())
    lower = html.lower()
    i = lower.find("<head>")
    if i != -1:
        return html[: i + 6] + str(base) + html[i + 6 :]
    return str(base) + html


def _get_template(template_id) -> InvoiceHtmlTemplate:
    tpl = db.session.get(InvoiceHtmlTemplate, template_id)
    if tpl is None or tpl.is_deleted:
        abort(404)
    return tpl


def _read_upload(file_storage):
    if not file_storage or not file_storage.filename:
        raise TemplateError(_("Choose an .html file"))
    if not file_storage.filename.lower().endswith((".html", ".htm")):
        raise TemplateError(_("Upload an .html file"))
    data = file_storage.read(MAX_TEMPLATE_BYTES + 1)
    if len(data) > MAX_TEMPLATE_BYTES:
        raise TemplateError(_("Template is larger than %(kb)s KB", kb=MAX_TEMPLATE_BYTES // 1024))
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise TemplateError(_("The file is not UTF-8 text")) from exc


def _filename_stem(filename: str) -> str:
    stem = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return stem.rsplit(".", 1)[0].strip()[:120] or "template"


def _snippet(code: str) -> str:
    if code == "rows":
        return "{% for row in rows %}\n  {{ row.description }} {{ money(row.total) }}\n{% endfor %}"
    return "{{ " + code + " }}"


def _edit_context(**kwargs):
    ctx = dict(
        variables=[(code, hint, _snippet(code)) for code, hint in TEMPLATE_VARIABLES],
        logo_snippet='{% if seller.logo %}<img src="{{ seller.logo }}" alt="">{% endif %}',
        is_builtin=bool(getattr(kwargs.get("template"), "builtin", None)),
        fonts=available_fonts(),
        preview_choices=_preview_choices(),
        preview_invoice=request.values.get("preview_invoice") or (_preview_choices()[0][0]),
        error=None,
        readonly=False,
    )
    ctx.update(kwargs)
    return ctx


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@invoice_templates_bp.route("/admin/invoice-templates")
@login_required
@admin_or_permission_required("manage_settings")
def list_templates():
    templates = InvoiceHtmlTemplate.active().order_by(InvoiceHtmlTemplate.name).all()
    builtins = [
        SimpleNamespace(name=n, ref=f"builtin:{n}", description=BUILTIN_DESCRIPTIONS.get(n, ""))
        for n in builtin_names()
    ]
    return render_template(
        "admin/invoice_templates/list.html",
        templates=templates,
        builtins=builtins,
        used_by=used_by(),
        active_tab="html",
    )


# ---------------------------------------------------------------------------
# Create / edit
# ---------------------------------------------------------------------------


def _save(tpl: InvoiceHtmlTemplate, *, is_new: bool):
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip()[:255] or None
    html = (request.form.get("html") or "").replace("\r\n", "\n")
    preview_value = request.form.get("preview_invoice")

    form_state = SimpleNamespace(id=tpl.id, name=name, description=description, html=html, is_new=is_new)

    if not name:
        return (
            render_template(
                "admin/invoice_templates/edit.html",
                **_edit_context(template=form_state, error={"error": _("Give the template a name"), "line": None}),
            ),
            400,
        )
    if InvoiceHtmlTemplate.name_taken(name, exclude_id=tpl.id):
        return (
            render_template(
                "admin/invoice_templates/edit.html",
                **_edit_context(
                    template=form_state, error={"error": _("A template with this name already exists"), "line": None}
                ),
            ),
            400,
        )

    invoice = _preview_invoice(preview_value)
    try:
        validate_template(html, invoice, _preview_settings(invoice))
    except TemplateError as exc:
        db.session.rollback()
        return (
            render_template(
                "admin/invoice_templates/edit.html",
                **_edit_context(template=form_state, error=exc.as_dict()),
            ),
            400,
        )

    tpl.name = name
    tpl.description = description
    tpl.html = html
    tpl.updated_by = current_user.id
    if is_new:
        tpl.created_by = current_user.id
        db.session.add(tpl)
        db.session.flush()
    tpl.save_version(current_user.id)
    if not safe_commit("invoice_template_save"):
        flash(_("Could not save the template. Please try again."), "error")
        return redirect(url_for("invoice_templates.list_templates"))
    flash(_("Template saved"), "success")
    return redirect(url_for("invoice_templates.edit_template", template_id=tpl.id, preview_invoice=preview_value))


@invoice_templates_bp.route("/admin/invoice-templates/new", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_settings")
@limiter.limit("30 per minute", methods=["POST"])
def new_template():
    if request.method == "POST":
        return _save(InvoiceHtmlTemplate(source="created"), is_new=True)
    start = builtin_source("simple") or ""
    form_state = SimpleNamespace(id=None, name="", description="", html=start, is_new=True)
    return render_template("admin/invoice_templates/edit.html", **_edit_context(template=form_state))


@invoice_templates_bp.route("/admin/invoice-templates/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("manage_settings")
@limiter.limit("30 per minute", methods=["POST"])
def edit_template(template_id):
    tpl = _get_template(template_id)
    if request.method == "POST":
        return _save(tpl, is_new=False)
    form_state = SimpleNamespace(
        id=tpl.id,
        name=tpl.name,
        description=tpl.description or "",
        html=tpl.html,
        is_new=False,
        version=tpl.version_number,
        updated_at=tpl.updated_at,
        updater=tpl.updater,
    )
    return render_template("admin/invoice_templates/edit.html", **_edit_context(template=form_state))


@invoice_templates_bp.route("/admin/invoice-templates/builtin/<name>")
@login_required
@admin_or_permission_required("manage_settings")
def view_builtin(name):
    source = builtin_source(name)
    if source is None:
        abort(404)
    form_state = SimpleNamespace(
        id=None, name=name, description=BUILTIN_DESCRIPTIONS.get(name, ""), html=source, is_new=False, builtin=name
    )
    return render_template("admin/invoice_templates/edit.html", **_edit_context(template=form_state, readonly=True))


# ---------------------------------------------------------------------------
# Upload / download / duplicate / delete
# ---------------------------------------------------------------------------


@invoice_templates_bp.route("/admin/invoice-templates/upload", methods=["POST"])
@login_required
@admin_or_permission_required("manage_settings")
@limiter.limit("20 per minute")
def upload_template():
    file_storage = request.files.get("file")
    try:
        html = _read_upload(file_storage)
        invoice = _preview_invoice(_preview_choices()[0][0])
        validate_template(html, invoice, _preview_settings(invoice))
    except TemplateError as exc:
        where = f" (line {exc.line})" if exc.line else ""
        hint = f" Did you mean {exc.hint}?" if exc.hint else ""
        flash(_("Template not uploaded: %(err)s", err=f"{exc.message}{where}.{hint}"), "error")
        return redirect(url_for("invoice_templates.list_templates"))

    tpl = InvoiceHtmlTemplate(
        name=InvoiceHtmlTemplate.free_name(_filename_stem(file_storage.filename)),
        html=html.replace("\r\n", "\n"),
        source="uploaded",
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.session.add(tpl)
    db.session.flush()
    tpl.save_version(current_user.id)
    if not safe_commit("invoice_template_upload"):
        flash(_("Could not save the template. Please try again."), "error")
        return redirect(url_for("invoice_templates.list_templates"))
    flash(_('Template uploaded as "%(name)s"', name=tpl.name), "success")
    return redirect(url_for("invoice_templates.edit_template", template_id=tpl.id))


def _download(name: str, html: str):
    return send_file(
        io.BytesIO(html.encode("utf-8")),
        mimetype="text/html",
        as_attachment=True,
        download_name=f"{name}.html",
    )


@invoice_templates_bp.route("/admin/invoice-templates/<int:template_id>/download")
@login_required
@admin_or_permission_required("manage_settings")
def download_template(template_id):
    tpl = _get_template(template_id)
    return _download(tpl.name, tpl.html)


@invoice_templates_bp.route("/admin/invoice-templates/builtin/<name>/download")
@login_required
@admin_or_permission_required("manage_settings")
def download_builtin(name):
    source = builtin_source(name)
    if source is None:
        abort(404)
    return _download(name, source)


def _duplicate(name: str, html: str, description=None):
    tpl = InvoiceHtmlTemplate(
        name=InvoiceHtmlTemplate.free_name(f"{name} copy"),
        description=description,
        html=html,
        source="duplicated",
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.session.add(tpl)
    db.session.flush()
    tpl.save_version(current_user.id)
    if not safe_commit("invoice_template_duplicate"):
        flash(_("Could not copy the template. Please try again."), "error")
        return redirect(url_for("invoice_templates.list_templates"))
    flash(_('Copied as "%(name)s"', name=tpl.name), "success")
    return redirect(url_for("invoice_templates.edit_template", template_id=tpl.id))


@invoice_templates_bp.route("/admin/invoice-templates/<int:template_id>/duplicate", methods=["POST"])
@login_required
@admin_or_permission_required("manage_settings")
def duplicate_template(template_id):
    tpl = _get_template(template_id)
    return _duplicate(tpl.name, tpl.html, tpl.description)


@invoice_templates_bp.route("/admin/invoice-templates/builtin/<name>/duplicate", methods=["POST"])
@login_required
@admin_or_permission_required("manage_settings")
def duplicate_builtin(name):
    source = builtin_source(name)
    if source is None:
        abort(404)
    return _duplicate(name, source, BUILTIN_DESCRIPTIONS.get(name))


@invoice_templates_bp.route("/admin/invoice-templates/<int:template_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("manage_settings")
def delete_template(template_id):
    tpl = _get_template(template_id)
    on_template_deleted(tpl)
    if not safe_commit("invoice_template_delete"):
        flash(_("Could not delete the template. Please try again."), "error")
        return redirect(url_for("invoice_templates.edit_template", template_id=template_id))
    flash(
        _('Template "%(name)s" deleted. Whatever used it now prints with the Visual layout.', name=tpl.name), "success"
    )
    return redirect(url_for("invoice_templates.list_templates"))


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


@invoice_templates_bp.route("/admin/invoice-templates/preview", methods=["POST"])
@login_required
@admin_or_permission_required("manage_settings")
@limiter.limit("120 per minute")
def preview():
    data = request.get_json(silent=True) or request.form
    html = data.get("html") or ""
    invoice = _preview_invoice(data.get("invoice"))
    try:
        if len(html.encode("utf-8")) > MAX_TEMPLATE_BYTES:
            raise TemplateError(_("Template is larger than %(kb)s KB", kb=MAX_TEMPLATE_BYTES // 1024))
        rendered = render_invoice_html(html, invoice, _preview_settings(invoice), strict=True)
    except TemplateError as exc:
        return jsonify(exc.as_dict()), 200
    return jsonify({"html": _with_asset_base(rendered)})


@invoice_templates_bp.route("/admin/invoice-templates/preview.pdf", methods=["POST"])
@login_required
@admin_or_permission_required("manage_settings")
@limiter.limit("30 per minute")
def preview_pdf():
    html = request.form.get("html") or ""
    invoice = _preview_invoice(request.form.get("invoice"))
    settings = _preview_settings(invoice)
    try:
        rendered = render_invoice_html(html, invoice, settings, strict=True)
        pdf = html_to_pdf(rendered, settings)
    except TemplateError as exc:
        where = f" (line {exc.line})" if exc.line else ""
        return f"{exc.message}{where}", 400, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception:  # WeasyPrint failure: details go to the log, not to the browser
        current_app.logger.exception("Invoice template preview PDF failed")
        return (
            _("PDF could not be built. Details are in the server log."),
            400,
            {"Content-Type": "text/plain; charset=utf-8"},
        )
    return send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=False, download_name="preview.pdf")


@invoice_templates_bp.route("/admin/invoice-templates/assets/<path:path>")
@login_required
@admin_or_permission_required("manage_settings")
def asset(path):
    """Fonts and the logo for the browser preview (the PDF gets them from its own fetcher)."""
    if path == "logo":
        logo = _logo_path(_settings())
        if logo is None:
            abort(404)
        return send_file(str(logo))
    if path.startswith("fonts/"):
        font = font_files().get(path[len("fonts/") :])
        if font is not None:
            return send_file(str(font))
    abort(404)


# ---------------------------------------------------------------------------
# For other pages (Settings, legal entities, invoice view)
# ---------------------------------------------------------------------------


@invoice_templates_bp.record_once
def _register_template_helpers(state):
    """Jinja globals (not a context processor) so they also work inside imported macros."""
    state.app.jinja_env.globals.update(_template_helpers())


def _template_helpers():
    return {
        "invoice_template_choices": template_choices,
        "invoice_template_label": ref_label,
        "invoice_templates_entities_with_own": entities_with_own_template,
        "invoice_uses_visual_layout": uses_visual_layout,
        "settings_default_invoice_template": default_template_ref,
    }
