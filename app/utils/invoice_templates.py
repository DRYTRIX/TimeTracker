"""Which template an invoice PDF prints with.

A template is named by one string, so the layout designer, built-in HTML templates and
user HTML templates are picked from one list:

- ``visual``          – the stock layout designer (``InvoicePDFTemplate`` per page size)
- ``builtin:<name>``  – an HTML template shipped in ``app/templates/invoices/html_builtin/``
- ``html:<id>``       – an ``InvoiceHtmlTemplate`` written or uploaded in the app

Order (``resolve_invoice_template``):

1. the template frozen on the invoice when it left draft (``Invoice.pdf_template_ref`` and,
   for user templates, ``pdf_template_version_id``);
2. the template of the invoice's legal entity, when that module is there and the entity has one;
3. ``Settings.invoice_pdf_template``;
4. ``visual``.

An unknown or deleted reference reads as ``visual``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app import db

VISUAL = "visual"
BUILTIN_DIR = Path(__file__).resolve().parent.parent / "templates" / "invoices" / "html_builtin"
BUILTIN_DESCRIPTIONS = {
    "simple": "Logo, seller and client, line table with hours and rate, totals with VAT, bank details",
}
DRAFT = "draft"


@dataclass
class ResolvedTemplate:
    ref: str  # "visual", "builtin:<name>" or "html:<id>"
    html: Optional[str] = None  # None for visual
    version_id: Optional[int] = None
    name: str = "Visual layout"

    @property
    def is_visual(self) -> bool:
        return self.ref == VISUAL


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------


def parse_ref(ref: Optional[str]) -> Tuple[str, Optional[str]]:
    ref = (ref or "").strip()
    if ref.startswith("builtin:"):
        return "builtin", ref[len("builtin:") :]
    if ref.startswith("html:"):
        return "html", ref[len("html:") :]
    return VISUAL, None


def _builtin_files() -> Dict[str, Path]:
    """Built-in template files by name. Paths come from the folder listing, never from a request."""
    if not BUILTIN_DIR.is_dir():
        return {}
    return {p.stem: p for p in BUILTIN_DIR.glob("*.html")}


def builtin_names() -> List[str]:
    return sorted(_builtin_files())


def builtin_source(name: str) -> Optional[str]:
    path = _builtin_files().get(name)
    return path.read_text(encoding="utf-8") if path else None


def _html_template(template_id) -> Optional["InvoiceHtmlTemplate"]:  # noqa: F821
    from app.models import InvoiceHtmlTemplate

    try:
        tid = int(template_id)
    except (TypeError, ValueError):
        return None
    tpl = db.session.get(InvoiceHtmlTemplate, tid)
    if tpl is None or tpl.is_deleted:
        return None
    return tpl


def load_ref(ref: Optional[str]) -> ResolvedTemplate:
    """The current state of a reference; unknown or deleted -> visual."""
    kind, value = parse_ref(ref)
    if kind == "builtin":
        source = builtin_source(value)
        if source is not None:
            return ResolvedTemplate(ref=f"builtin:{value}", html=source, name=f"{value} (built-in)")
    elif kind == "html":
        tpl = _html_template(value)
        if tpl is not None:
            version = tpl.current_version
            return ResolvedTemplate(
                ref=tpl.ref, html=tpl.html, version_id=version.id if version else None, name=tpl.name
            )
    return ResolvedTemplate(ref=VISUAL)


def ref_exists(ref: Optional[str]) -> bool:
    if (ref or VISUAL) == VISUAL:
        return True
    return not load_ref(ref).is_visual


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def _entity_ref(invoice) -> Optional[str]:
    """Template chosen on the invoice's legal entity, if the legal-entities module is there."""
    entity = getattr(invoice, "billing_entity", None)
    ref = getattr(entity, "pdf_template", None) if entity is not None else None
    return ref or None


def _settings_ref(settings=None) -> str:
    if settings is None:
        from app.models import Settings

        # A plain read: Settings.get_settings() may create and commit the row, which must not
        # happen from inside the Invoice.status listener.
        with db.session.no_autoflush:
            settings = Settings.query.first()
    try:
        return getattr(settings, "invoice_pdf_template", None) or VISUAL
    except Exception:
        return VISUAL


def default_template_ref(settings=None) -> str:
    """The template set in Settings for invoices whose legal entity has none."""
    return _settings_ref(settings)


def current_choice(invoice, settings=None) -> ResolvedTemplate:
    """Template the invoice would get now, ignoring anything frozen on it."""
    ref = _entity_ref(invoice) or _settings_ref(settings)
    return load_ref(ref)


def resolve_invoice_template(invoice, settings=None) -> ResolvedTemplate:
    frozen = getattr(invoice, "pdf_template_ref", None)
    if frozen:
        kind, value = parse_ref(frozen)
        if kind == "html":
            version_id = getattr(invoice, "pdf_template_version_id", None)
            if version_id:
                from app.models import InvoiceHtmlTemplateVersion

                version = db.session.get(InvoiceHtmlTemplateVersion, version_id)
                if version is not None:
                    tpl = version.template
                    return ResolvedTemplate(
                        ref=frozen,
                        html=version.html,
                        version_id=version.id,
                        name=tpl.name if tpl is not None else frozen,
                    )
            return load_ref(frozen)
        if kind == "builtin":
            return load_ref(frozen)
        return ResolvedTemplate(ref=VISUAL)
    status = getattr(invoice, "status", None) or DRAFT
    if status != DRAFT:
        # Left draft before HTML templates existed (or was imported as sent/paid): prints as it always did.
        return ResolvedTemplate(ref=VISUAL)
    return current_choice(invoice, settings)


def freeze_invoice_template(invoice, settings=None) -> None:
    """Fix the template on an invoice that is leaving draft. Safe to call more than once.

    Runs from a listener on ``Invoice.status`` (see ``app/models/invoice_html_template.py``),
    so every way an invoice stops being a draft is covered: status buttons, bulk status
    change, sending by e-mail, approval, payments, credit notes, the API. Draft invoices
    always print with the current choice; once frozen the invoice keeps its template and
    version for good.
    """
    if invoice is None or getattr(invoice, "pdf_template_ref", None):
        return
    try:
        resolved = current_choice(invoice, settings)
        invoice.pdf_template_ref = resolved.ref
        invoice.pdf_template_version_id = resolved.version_id if resolved.ref.startswith("html:") else None
    except Exception:  # never block a status change because of the PDF template
        try:
            from flask import current_app

            current_app.logger.exception("Could not freeze the PDF template of invoice %s", getattr(invoice, "id", "?"))
        except Exception:
            pass


def uses_visual_layout(invoice, settings=None) -> bool:
    try:
        return resolve_invoice_template(invoice, settings).is_visual
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Lists for the UI
# ---------------------------------------------------------------------------


def template_choices() -> List[Tuple[str, str]]:
    """(ref, label) for select boxes: user templates, built-ins, Visual layout."""
    from app.models import InvoiceHtmlTemplate

    choices = [(t.ref, t.name) for t in InvoiceHtmlTemplate.active().order_by(InvoiceHtmlTemplate.name).all()]
    choices += [(f"builtin:{n}", f"{n} (built-in)") for n in builtin_names()]
    choices.append((VISUAL, "Visual layout"))
    return choices


def ref_label(ref: Optional[str]) -> str:
    return load_ref(ref).name


def _entities_with_templates() -> list:
    """Legal entities that picked their own template, when that module is installed."""
    try:
        from app.models import BillingEntity  # type: ignore[attr-defined]
    except ImportError:
        return []
    if not hasattr(BillingEntity, "pdf_template"):
        return []
    try:
        return BillingEntity.query.filter(BillingEntity.pdf_template.isnot(None)).all()
    except Exception:
        return []


def entities_with_own_template() -> List[Tuple[object, str]]:
    return [(e, e.pdf_template) for e in _entities_with_templates()]


def used_by() -> Dict[str, List[str]]:
    """ref -> who prints with it: 'Default' (Settings) and legal entity names."""
    result: Dict[str, List[str]] = {}
    default_ref = _settings_ref()
    result.setdefault(default_ref, []).append("Default")
    for entity in _entities_with_templates():
        name = getattr(entity, "short_name", None) or getattr(entity, "legal_name", None) or str(entity.id)
        result.setdefault(entity.pdf_template, []).append(name)
    return result


def on_template_deleted(template, settings=None) -> None:
    """Everything that pointed at a deleted template prints with the Visual layout."""
    ref = template.ref
    if settings is None:
        from app.models import Settings

        settings = Settings.get_settings()
    if getattr(settings, "invoice_pdf_template", None) == ref:
        settings.invoice_pdf_template = VISUAL
    for entity in _entities_with_templates():
        if entity.pdf_template == ref:
            entity.pdf_template = VISUAL
    template.deleted_at = datetime.utcnow()
