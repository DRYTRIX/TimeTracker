import re
from datetime import datetime

DEFAULT_INVOICE_PATTERN = "{PREFIX}-{YYYY}{MM}{DD}-{SEQ}"
DEFAULT_QUOTE_PATTERN = "{PREFIX}-{YYYY}{MM}{DD}-{SEQ}"
_ALLOWED_TOKENS = {"SEQ", "YYYY", "YY", "MM", "DD", "PREFIX"}


def sanitize_invoice_prefix(prefix_value):
    """Normalize legacy prefix input while allowing empty values."""
    if prefix_value is None:
        return ""
    return str(prefix_value).strip()


def sanitize_invoice_pattern(pattern_value):
    """Normalize pattern input while allowing empty values."""
    if pattern_value is None:
        return ""
    return str(pattern_value).strip()


def validate_invoice_pattern(pattern_value):
    """Validate invoice number pattern and return (ok, error_message)."""
    pattern = sanitize_invoice_pattern(pattern_value)
    if not pattern:
        return True, ""

    tokens = re.findall(r"\{([A-Z]+)\}", pattern)
    if not tokens:
        return False, "Pattern must include at least one token such as {SEQ}."

    invalid_tokens = sorted({token for token in tokens if token not in _ALLOWED_TOKENS})
    if invalid_tokens:
        return False, f"Unsupported token(s): {', '.join(invalid_tokens)}"

    if "SEQ" not in tokens:
        return False, "Pattern must include {SEQ}."

    return True, ""


def resolve_pattern(raw_pattern):
    """Resolve the effective pattern with compatibility fallback."""
    pattern = sanitize_invoice_pattern(raw_pattern)
    if pattern:
        return pattern
    return "{SEQ}"


def resolve_invoice_pattern(settings):
    """Resolve the effective invoice pattern from settings with compatibility fallback."""
    return resolve_pattern(getattr(settings, "invoice_number_pattern", ""))


def resolve_quote_pattern(settings):
    """Resolve the effective quote pattern from settings with compatibility fallback."""
    return resolve_pattern(getattr(settings, "quote_number_pattern", ""))


def _normalize_start_number(start_number):
    try:
        normalized = int(start_number)
        return max(1, normalized)
    except (TypeError, ValueError):
        return 1


def _build_token_values(now, prefix):
    return {
        "YYYY": now.strftime("%Y"),
        "YY": now.strftime("%y"),
        "MM": now.strftime("%m"),
        "DD": now.strftime("%d"),
        "PREFIX": prefix,
    }


def _materialize_pattern_without_seq(pattern, token_values):
    rendered = pattern
    for key, value in token_values.items():
        rendered = rendered.replace(f"{{{key}}}", value)
    return rendered


def _extract_seq_width(pattern):
    return max(3, len(re.findall(r"\{SEQ\}", pattern)))


def _db_dialect_name():
    from app import db

    bind = db.session.get_bind()
    return (bind.dialect.name if bind else "") or ""


def _lock_settings_for_numbering():
    """Serialize document number allocation via the Settings singleton row.

    PostgreSQL: ``SELECT ... FOR UPDATE`` on the Settings row (held until the
    current transaction commits/rolls back).

    SQLite: best-effort ``BEGIN IMMEDIATE`` when no transaction is active;
    ``with_for_update`` is a no-op on SQLite, so callers should also use
    ``generate_next_invoice_number_with_retry`` when inserting under concurrency.
    """
    from sqlalchemy import text

    from app import db
    from app.models import Settings

    dialect = _db_dialect_name()
    if dialect == "sqlite":
        try:
            # Only start IMMEDIATE when the session has not already begun a txn.
            if not db.session.in_transaction():
                db.session.execute(text("BEGIN IMMEDIATE"))
        except Exception:
            # Best-effort; unique constraint + retry covers residual races.
            import logging

            logging.getLogger(__name__).debug(
                "SQLite BEGIN IMMEDIATE for invoice numbering failed; continuing",
                exc_info=True,
            )

    settings = Settings.query.with_for_update().first()
    if settings is None:
        settings = Settings.get_settings()
        db.session.flush()
        settings = Settings.query.with_for_update().filter_by(id=settings.id).first() or settings
    return settings


def generate_next_document_number(
    document_model,
    number_field,
    prefix,
    pattern,
    start_number,
    document_query=None,
    now=None,
    *,
    lock_settings=False,
):
    """Generate next document number for the given pattern and settings values.

    When ``lock_settings`` is True (PostgreSQL/SQLite numbering paths), acquires a
    row lock on Settings before scanning existing numbers to reduce TOCTOU races.
    """
    if lock_settings:
        _lock_settings_for_numbering()

    now = now or datetime.utcnow()
    prefix = sanitize_invoice_prefix(prefix)
    start_number = _normalize_start_number(start_number)
    pattern = resolve_pattern(pattern)

    token_values = _build_token_values(now, prefix)
    materialized = _materialize_pattern_without_seq(pattern, token_values)
    seq_placeholder = "{SEQ}"

    if seq_placeholder not in materialized:
        materialized = f"{materialized}{seq_placeholder}"

    seq_width = _extract_seq_width(materialized)
    regex_pattern = "^" + re.escape(materialized).replace(re.escape(seq_placeholder), r"(?P<seq>\d+)") + "$"
    seq_regex = re.compile(regex_pattern)

    first_seq_idx = materialized.index(seq_placeholder)
    prefix_probe = materialized[:first_seq_idx]

    query = document_query or document_model.query
    if prefix_probe:
        query = query.filter(number_field.startswith(prefix_probe))

    max_seq = None
    for (document_number,) in query.with_entities(number_field).all():
        if not document_number:
            continue
        match = seq_regex.match(document_number)
        if not match:
            continue
        try:
            seq_value = int(match.group("seq"))
        except (TypeError, ValueError):
            continue
        max_seq = seq_value if max_seq is None else max(max_seq, seq_value)

    if max_seq is None:
        next_seq = start_number
    else:
        next_seq = max(max_seq + 1, start_number)

    return materialized.replace(seq_placeholder, f"{next_seq:0{seq_width}d}", 1)


def generate_next_invoice_number(invoice_model, invoice_query=None, settings=None, now=None):
    """Generate next invoice number for the current pattern and settings.

    Locks the Settings singleton before scanning invoice numbers (see
    ``_lock_settings_for_numbering``) so concurrent allocators serialize.
    Prefer ``allocate_next_invoice_number`` at call sites that insert.
    """
    locked_settings = _lock_settings_for_numbering()
    if settings is None:
        settings = locked_settings

    now = now or datetime.utcnow()
    prefix = sanitize_invoice_prefix(getattr(settings, "invoice_prefix", ""))
    start_number = _normalize_start_number(getattr(settings, "invoice_start_number", 1))
    pattern = resolve_invoice_pattern(settings)

    return generate_next_document_number(
        invoice_model,
        invoice_model.invoice_number,
        prefix,
        pattern,
        start_number,
        document_query=invoice_query,
        now=now,
        lock_settings=False,  # already locked above
    )


def allocate_next_invoice_number(invoice_model, invoice_query=None, settings=None, now=None):
    """Lock Settings, compute the next invoice number, and return it.

    Callers are responsible for inserting the invoice (ideally in the same
    transaction so the Settings row lock covers the insert).
    """
    return generate_next_invoice_number(
        invoice_model,
        invoice_query=invoice_query,
        settings=settings,
        now=now,
    )


def generate_next_invoice_number_with_retry(
    create_fn,
    *,
    invoice_model=None,
    max_attempts=5,
    invoice_query=None,
    settings=None,
    now=None,
):
    """Allocate an invoice number and call ``create_fn(number)``, retrying on conflict.

    Retries up to ``max_attempts`` times when ``create_fn`` raises
    ``IntegrityError`` (typically a unique ``invoice_number`` collision under
    SQLite or a race that slipped the Settings lock). The session is rolled
    back before each retry.

    ``create_fn`` should insert the invoice (flush/commit as appropriate) and
    return whatever the caller needs.
    """
    from sqlalchemy.exc import IntegrityError

    from app import db

    if invoice_model is None:
        from app.models import Invoice

        invoice_model = Invoice

    last_error = None
    for _ in range(max_attempts):
        try:
            number = allocate_next_invoice_number(
                invoice_model,
                invoice_query=invoice_query,
                settings=settings,
                now=now,
            )
            return create_fn(number)
        except IntegrityError as exc:
            last_error = exc
            db.session.rollback()
            continue

    if last_error is not None:
        raise last_error
    raise RuntimeError("Invoice number allocation failed with no attempts")


def generate_next_quote_number(quote_model, quote_query=None, settings=None, now=None):
    """Generate next quote number for the current pattern and settings.

    Locks Settings before scanning, same as invoice numbering.
    """
    locked_settings = _lock_settings_for_numbering()
    if settings is None:
        settings = locked_settings

    if now is None:
        from app.utils.timezone import now_in_app_timezone

        now = now_in_app_timezone().replace(tzinfo=None)

    prefix = sanitize_invoice_prefix(getattr(settings, "quote_prefix", ""))
    start_number = _normalize_start_number(getattr(settings, "quote_start_number", 1))
    pattern = resolve_quote_pattern(settings)

    return generate_next_document_number(
        quote_model,
        quote_model.quote_number,
        prefix,
        pattern,
        start_number,
        document_query=quote_query,
        now=now,
        lock_settings=False,
    )
