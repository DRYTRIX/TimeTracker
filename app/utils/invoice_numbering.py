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


def generate_next_document_number(
    document_model,
    number_field,
    prefix,
    pattern,
    start_number,
    document_query=None,
    now=None,
):
    """Generate next document number for the given pattern and settings values."""
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
    """Generate next invoice number for the current pattern and settings."""
    if settings is None:
        from app.models import Settings

        settings = Settings.get_settings()

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
    )


def generate_next_quote_number(quote_model, quote_query=None, settings=None, now=None):
    """Generate next quote number for the current pattern and settings."""
    if settings is None:
        from app.models import Settings

        settings = Settings.get_settings()

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
    )
