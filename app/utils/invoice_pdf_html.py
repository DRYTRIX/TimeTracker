"""Invoice PDF from an HTML template.

A template is one HTML page with its own ``<style>``, laid out in normal document flow.
It is rendered with Jinja in a sandbox and turned into a PDF by WeasyPrint, so long
tables break across pages on their own and repeat their header. The same HTML is the
browser preview, so the preview is what ends up in the PDF.

Which template an invoice uses is decided in ``app/utils/invoice_templates.py``.

Safety: templates are written by admins and may be uploaded as files, so

- Jinja runs in ``SandboxedEnvironment`` (no ``__class__`` tricks, no Flask globals);
- WeasyPrint gets a URL fetcher that serves only the bundled fonts (``fonts/<file>``),
  the seller's logo (``logo``) and small ``data:`` URIs. No server files, no network.
"""

from __future__ import annotations

import difflib
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from flask import current_app
from jinja2 import StrictUndefined, TemplateSyntaxError, Undefined, UndefinedError
from jinja2.sandbox import SandboxedEnvironment, SecurityError
from markupsafe import Markup, escape

DEFAULT_DATE_FORMAT = "%d/%m/%Y"
MAX_TEMPLATE_BYTES = 512 * 1024
MAX_DATA_URI_BYTES = 1024 * 1024

FONTS_DIR = Path(__file__).resolve().parent.parent / "resources" / "fonts"
ASSET_BASE = "https://tt-assets.invalid/"  # never fetched from the network: see AssetFetcher

# Variables a template can use. Shown on the edit page; used for "did you mean" hints.
TEMPLATE_VARIABLES = [
    ("invoice.invoice_number", "Invoice number"),
    ("invoice.issue_date", "Issue date (use doc_date)"),
    ("invoice.due_date", "Due date (use doc_date)"),
    ("invoice.status", "Status"),
    ("seller.name", "Our company or legal entity"),
    ("seller.tax_id", "Our tax ID (VAT number, else registration number)"),
    ("seller.vat_number", "Our VAT number"),
    ("seller.registration_number", "Our registration number"),
    ("seller.address", "Our address"),
    ("seller.country", "Our country code"),
    ("seller.email", "Our e-mail"),
    ("seller.phone", "Our phone"),
    ("seller.website", "Our website"),
    ("seller.logo", "Logo address for <img src>, empty if none"),
    ("payment_details", "Where to pay: bank details as printed"),
    ("buyer.name", "Client name (Bill to legal entity, else client)"),
    ("buyer.tax_id", "Client tax number (VAT number, else registration number)"),
    ("buyer.vat_number", "Client VAT number"),
    ("buyer.registration_number", "Client registration number"),
    ("buyer.country", "Client country code"),
    ("buyer.address", "Client address"),
    ("buyer.email", "Client e-mail"),
    ("buyer.bank_info", "Client bank details (client custom field bank_details)"),
    ("rows", "Invoice lines: row.number, row.description, row.quantity, row.unit_price, row.total"),
    ("show_hours", "True if any line has a quantity other than 1"),
    ("currency", "Invoice currency"),
    ("subtotal", "Subtotal"),
    ("tax_rate", "VAT rate, %"),
    ("tax_amount", "VAT amount"),
    ("discount", "Discount amount"),
    ("show_breakdown", "True if there is VAT or a discount"),
    ("total", "Total to pay"),
    ("payment_purpose", "Invoice notes"),
    ("terms", "Invoice terms, else default terms from Settings"),
    ("money(x)", "16666.66 -> 16 666.66"),
    ("qty(x)", "24.50 -> 24.5"),
    ("doc_date(d)", "Date as 30/10/2026; doc_date(d, '%d.%m.%Y') for another format"),
    ("lines(text)", "Text with its line breaks kept"),
    ("paragraphs(text)", "Blank line = new paragraph"),
]


# ---------------------------------------------------------------------------
# Formatting helpers (template functions)
# ---------------------------------------------------------------------------


def _to_decimal(value: Any) -> Decimal:
    if value is None or value == "" or isinstance(value, Undefined):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def format_amount(value: Any, thousands: str = " ", decimals: int = 2) -> str:
    """16666.66 -> '16 666.66' (non-breaking space between thousands)."""
    number = _to_decimal(value).quantize(Decimal(1).scaleb(-decimals))
    return f"{number:,.{decimals}f}".replace(",", thousands)


def format_quantity(value: Any) -> str:
    """Hours without trailing zeros: 96 -> '96', 24.50 -> '24.5'."""
    return f"{_to_decimal(value).normalize():f}"


def format_doc_date(value: Any, fmt: Optional[str] = None) -> str:
    if not value or isinstance(value, Undefined):
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        value = value.date()
    if not isinstance(value, date):
        return str(value)
    return value.strftime(fmt or DEFAULT_DATE_FORMAT)


def text_lines(value: Any) -> Markup:
    """Escape text and keep its line breaks."""
    if not value or isinstance(value, Undefined):
        return Markup("")
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    return Markup("<br>").join(escape(line) for line in text.split("\n"))


def text_paragraphs(value: Any) -> Markup:
    """Blank line = new paragraph, single line break = <br>."""
    if not value or isinstance(value, Undefined):
        return Markup("")
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks = [b for b in re.split(r"\n\s*\n", text) if b.strip()]
    return Markup("").join(Markup("<p>") + text_lines(b) + Markup("</p>") for b in blocks)


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


def _as_list(rel: Any) -> list:
    if rel is None:
        return []
    if hasattr(rel, "all"):
        try:
            return list(rel.all())
        except Exception:
            return []
    try:
        return list(rel)
    except TypeError:
        return []


def _line_items(invoice) -> List[SimpleNamespace]:
    """Items, extra goods and billed expenses as one list of rows."""
    rows: List[SimpleNamespace] = []

    items = _as_list(getattr(invoice, "items", None))
    items.sort(key=lambda i: (getattr(i, "position", 0) or 0, getattr(i, "id", 0) or 0))
    for item in items:
        rows.append(
            SimpleNamespace(
                description=getattr(item, "description", "") or "",
                quantity=_to_decimal(getattr(item, "quantity", 1)),
                unit_price=_to_decimal(getattr(item, "unit_price", 0)),
                total=_to_decimal(getattr(item, "total_amount", 0)),
            )
        )

    for good in _as_list(getattr(invoice, "extra_goods", None)):
        parts = [getattr(good, "name", "") or ""]
        if getattr(good, "description", None):
            parts.append(str(good.description))
        rows.append(
            SimpleNamespace(
                description="\n".join(p for p in parts if p),
                quantity=_to_decimal(getattr(good, "quantity", 1)),
                unit_price=_to_decimal(getattr(good, "unit_price", 0)),
                total=_to_decimal(getattr(good, "total_amount", 0)),
            )
        )

    for expense in _as_list(getattr(invoice, "expenses", None)):
        parts = [getattr(expense, "title", "") or ""]
        if getattr(expense, "description", None):
            parts.append(str(expense.description))
        amount = _to_decimal(getattr(expense, "total_amount", None) or getattr(expense, "amount", 0))
        rows.append(
            SimpleNamespace(
                description="\n".join(p for p in parts if p),
                quantity=Decimal("1"),
                unit_price=amount,
                total=amount,
            )
        )

    for index, row in enumerate(rows, start=1):
        row.number = index
    return rows


def _logo_path(settings) -> Optional[Path]:
    try:
        if settings is not None and settings.has_logo():
            path = settings.get_logo_path()
            if path and Path(path).is_file():
                return Path(path)
    except Exception:
        pass
    return None


def _seller(settings) -> SimpleNamespace:
    """Who issues the invoice, read from ``settings`` (the invoice's own seller when the
    PDF generator passes legal-entity settings, else the company from Settings)."""

    def get(attr: str) -> str:
        return str(getattr(settings, attr, "") or "").strip() if settings is not None else ""

    vat = get("company_vat_number") or get("company_tax_id")
    return SimpleNamespace(
        name=get("company_name"),
        tax_id=get("company_tax_id"),
        vat_number=vat,
        registration_number=get("company_registration_number") or get("company_tax_id"),
        address=get("company_address"),
        country=get("company_country"),
        email=get("company_email"),
        phone=get("company_phone"),
        website=get("company_website"),
        logo="logo" if _logo_path(settings) else "",
    )


def _buyer(invoice) -> SimpleNamespace:
    """Who is billed: the invoice's Bill to legal entity (its snapshot) when there is one, else the client."""
    client = getattr(invoice, "client", None)
    custom = getattr(client, "custom_fields", None) or {}
    if not isinstance(custom, dict):
        custom = {}
    snap = getattr(invoice, "buyer_snapshot", None) or {}
    if not isinstance(snap, dict):
        snap = {}

    def pick(*values) -> str:
        for value in values:
            if value:
                return str(value).strip()
        return ""

    vat = pick(snap.get("vat_number"), getattr(client, "vat_id", None))
    registration = pick(snap.get("registration_number"))
    return SimpleNamespace(
        name=pick(snap.get("legal_name"), getattr(invoice, "client_name", None), getattr(client, "name", None)),
        tax_id=vat or registration,
        vat_number=vat,
        registration_number=registration,
        country=pick(snap.get("country"), getattr(client, "country", None)),
        address=pick(snap.get("address"), getattr(invoice, "client_address", None), getattr(client, "address", None)),
        email=pick(snap.get("email"), getattr(invoice, "client_email", None), getattr(client, "email", None)),
        bank_info=pick(custom.get("bank_details")),
    )


def build_context(invoice, settings=None) -> Dict[str, Any]:
    if settings is None:
        from app.models import Settings

        settings = Settings.get_settings()

    rows = _line_items(invoice)
    subtotal = _to_decimal(getattr(invoice, "subtotal", None))
    tax_amount = _to_decimal(getattr(invoice, "tax_amount", None))
    discount = _to_decimal(getattr(invoice, "discount_amount", None))
    total = _to_decimal(getattr(invoice, "total_amount", None))
    if not total and rows:
        total = sum((r.total for r in rows), Decimal("0"))

    terms = getattr(invoice, "terms", None) or getattr(settings, "invoice_terms", None) or ""
    payment_details = (
        getattr(invoice, "payment_details_text", None)
        or getattr(settings, "payment_text", None)  # legal-entity seller: the raw Pay to text
        or getattr(settings, "company_bank_info", "")
    )

    return {
        "invoice": invoice,
        "seller": _seller(settings),
        "buyer": _buyer(invoice),
        "payment_details": (payment_details or "").strip(),
        "rows": rows,
        "show_hours": any(r.quantity != 1 for r in rows),
        "currency": (getattr(invoice, "currency_code", None) or getattr(settings, "currency", None) or "EUR"),
        "subtotal": subtotal,
        "tax_rate": _to_decimal(getattr(invoice, "tax_rate", None)),
        "tax_amount": tax_amount,
        "discount": discount,
        "show_breakdown": bool(tax_amount or discount),
        "total": total,
        "payment_purpose": getattr(invoice, "notes", None) or "",
        "terms": terms,
        "money": format_amount,
        "qty": format_quantity,
        "doc_date": format_doc_date,
        "lines": text_lines,
        "paragraphs": text_paragraphs,
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class TemplateError(Exception):
    """A template that cannot be rendered. ``line`` is 1-based when known."""

    def __init__(self, message: str, line: Optional[int] = None, hint: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.hint = hint

    def as_dict(self):
        return {"error": self.message, "line": self.line, "hint": self.hint}


def _environment(strict: bool) -> SandboxedEnvironment:
    # codeql[py/template-injection]: admin-authored invoice templates, sandboxed
    return SandboxedEnvironment(autoescape=True, undefined=StrictUndefined if strict else Undefined)


def _error_line(source: str, exc: Exception) -> Optional[int]:
    """Best effort: the template line an exception points to."""
    line = getattr(exc, "lineno", None)
    if line:
        return line
    tb = exc.__traceback__
    found = None
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == "<template>":
            found = tb.tb_lineno
        tb = tb.tb_next
    return found


def _undefined_name(message: str, source: str, line: Optional[int]) -> Optional[str]:
    """The name a template used that does not exist, e.g. ``buyer.vat``."""
    m = re.search(r"'([^']+)' is undefined", message)
    if m:
        return m.group(1)
    m = re.search(r"has no attribute '([^']+)'", message)
    if not m:
        return None
    attr = m.group(1)
    if line:
        lines = source.splitlines()
        if 0 < line <= len(lines):
            full = re.search(r"([A-Za-z_][\w]*(?:\.[A-Za-z_]\w*)*\." + re.escape(attr) + r")\b", lines[line - 1])
            if full:
                return full.group(1)
    return attr


_ALIASES = {
    "vat": "tax_id",
    "vat_id": "tax_id",
    "tax": "tax_id",
    "tax_number": "tax_id",
    "iban": "payment_details",
    "bank": "payment_details",
    "bank_details": "payment_details",
    "number": "invoice_number",
    "date": "issue_date",
    "items": "rows",
    "lines": "rows",
    "amount": "total",
}


def _closest_variable(name: str) -> Optional[str]:
    names = [v.split("(")[0] for v, _ in TEMPLATE_VARIABLES]
    head, _, tail = name.rpartition(".")
    alias = _ALIASES.get(tail)
    if alias:
        for candidate in (f"{head}.{alias}" if head else alias, alias):
            if candidate in names:
                return candidate
    match = difflib.get_close_matches(name, names, n=1, cutoff=0.6)
    if match:
        return match[0]
    tail = name.rsplit(".", 1)[-1]
    head = name.rsplit(".", 1)[0] if "." in name else ""
    same_head = [n for n in names if head and n.startswith(head + ".")]
    match = difflib.get_close_matches(f"{head}.{tail}" if head else tail, same_head or names, n=1, cutoff=0.4)
    return match[0] if match else None


def render_html_source(source: str, context: Dict[str, Any], strict: bool = False) -> str:
    """Render template ``source`` in the sandbox. Raises ``TemplateError``."""
    if source is None:
        source = ""
    try:
        template = _environment(strict).from_string(source)
    except TemplateSyntaxError as exc:
        raise TemplateError(f"Template syntax error: {exc.message}", line=exc.lineno) from exc
    try:
        return template.render(**context)
    except UndefinedError as exc:
        line = _error_line(source, exc)
        name = _undefined_name(str(exc), source, line)
        hint = _closest_variable(name) if name else None
        message = f"{name} is not a template variable" if name else str(exc)
        raise TemplateError(message, line=line, hint=hint) from exc
    except SecurityError as exc:
        raise TemplateError(f"Not allowed in a template: {exc}", line=_error_line(source, exc)) from exc
    except Exception as exc:  # any other Jinja/runtime error
        raise TemplateError(f"Template error: {exc}", line=_error_line(source, exc)) from exc


def _weasyprint_fetcher_class():
    from weasyprint.urls import URLFetcher, URLFetcherResponse

    class AssetFetcher(URLFetcher):
        """Serves only bundled fonts, the logo and small data: URIs."""

        def __init__(self, logo_path: Optional[Path] = None):
            super().__init__(allowed_protocols=("https", "data"), allow_redirects=False)
            self._logo_path = logo_path

        def fetch(self, url, headers=None):
            if url.startswith("data:"):
                if len(url) > MAX_DATA_URI_BYTES * 4 // 3 + 64:
                    raise ValueError("data: URI too large")
                return super().fetch(url, headers)
            if not url.startswith(ASSET_BASE):
                raise ValueError(f"Not allowed in invoice templates: {url}")
            rel = url[len(ASSET_BASE) :].split("?")[0].split("#")[0]
            if rel == "logo" and self._logo_path:
                return URLFetcherResponse(url, body=self._logo_path.read_bytes())
            if rel.startswith("fonts/"):
                font = font_files().get(rel[len("fonts/") :])
                if font is not None:
                    return URLFetcherResponse(url, body=font.read_bytes())
            raise ValueError(f"Not allowed in invoice templates: {url}")

    return AssetFetcher


def font_files() -> Dict[str, Path]:
    """Bundled font files by file name. Paths come from the folder listing, never from a request."""
    if not FONTS_DIR.is_dir():
        return {}
    return {p.name: p for p in FONTS_DIR.iterdir() if p.suffix.lower() in (".ttf", ".otf", ".woff", ".woff2")}


def available_fonts() -> List[str]:
    return sorted(font_files())


def html_to_pdf(html: str, settings=None) -> bytes:
    from weasyprint import HTML  # imported lazily: native deps (pango) are only needed here

    fetcher = _weasyprint_fetcher_class()(logo_path=_logo_path(settings))
    return HTML(string=html, base_url=ASSET_BASE, url_fetcher=fetcher).write_pdf()


def render_invoice_html(source: str, invoice, settings=None, strict: bool = False) -> str:
    return render_html_source(source, build_context(invoice, settings), strict=strict)


def render_invoice_pdf(source: str, invoice, settings=None) -> bytes:
    html = render_invoice_html(source, invoice, settings)
    return html_to_pdf(html, settings)


def validate_template(source: str, invoice, settings=None, build_pdf: bool = True) -> str:
    """Check a template before saving it. Returns the rendered HTML; raises ``TemplateError``."""
    if len((source or "").encode("utf-8")) > MAX_TEMPLATE_BYTES:
        raise TemplateError(f"Template is larger than {MAX_TEMPLATE_BYTES // 1024} KB")
    if not (source or "").strip():
        raise TemplateError("Template is empty")
    html = render_invoice_html(source, invoice, settings, strict=True)
    if build_pdf:
        try:
            html_to_pdf(html, settings)
        except TemplateError:
            raise
        except Exception as exc:
            raise TemplateError(f"PDF could not be built: {exc}") from exc
    return html


def safe_app_logger():
    try:
        return current_app.logger
    except RuntimeError:
        import logging

        return logging.getLogger(__name__)
