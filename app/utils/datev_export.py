"""DATEV EXTF Buchungsstapel CSV generator.

Produces a DATEV-compatible ASCII/CSV export (format header + booking lines)
suitable for import into DATEV Unternehmen online / Rechnungswesen.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable, List, Optional


def _money(value) -> str:
    try:
        d = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except Exception:
        d = Decimal("0.00")
    # DATEV uses comma as decimal separator
    return f"{d:.2f}".replace(".", ",")


def _safe(text: Optional[str], max_len: int = 60) -> str:
    if not text:
        return ""
    # Strip characters that break CSV; DATEV uses semicolon delimiter
    cleaned = str(text).replace(";", ",").replace("\n", " ").replace("\r", " ").strip()
    return cleaned[:max_len]


def build_datev_buchungsstapel(
    invoices: Iterable,
    *,
    consultant_number: str = "00000",
    client_number: str = "00000",
    account_revenue: str = "8400",
    account_receivable: str = "10000",
    fiscal_year_start: Optional[datetime] = None,
) -> str:
    """
    Build EXTF CSV content for DATEV Buchungsstapel.

    Each invoice becomes one booking line (Soll = receivables, Haben = revenue).
    """
    now = datetime.utcnow()
    fy_start = fiscal_year_start or datetime(now.year, 1, 1)
    # Header line (DATEV EXTF format descriptor — simplified)
    header = (
        f'"EXTF";700;21;"Buchungsstapel";7;'
        f"{now.strftime('%Y%m%d%H%M%S')};"
        f"{fy_start.strftime('%Y%m%d')};"
        f'4;"{_safe(consultant_number, 7)}";"{_safe(client_number, 5)}";'
        f'"";"";"TimeTracker";1;0\n'
    )
    # Column headers (subset of DATEV fields)
    columns = (
        "Umsatz (ohne Soll/Haben-Kz);Soll/Haben-Kennzeichen;WKZ Umsatz;"
        "Kurs;Basis-Umsatz;WKZ Basis-Umsatz;Konto;Gegenkonto (ohne BU-Schlüssel);"
        "BU-Schlüssel;Belegdatum;Belegfeld 1;Belegfeld 2;Skonto;"
        "Buchungstext;Postensperre;Diverse Adressnummer;Geschäftspartnerbank;"
        "Sachverhalt;Zinssperre;Beleglink\n"
    )

    lines: List[str] = [header, columns]
    for inv in invoices:
        amount = getattr(inv, "total_amount", None) or 0
        issue = getattr(inv, "issue_date", None) or now.date()
        belegdatum = issue.strftime("%d%m")
        belegfeld1 = _safe(getattr(inv, "invoice_number", "") or str(getattr(inv, "id", "")), 36)
        text = _safe(getattr(inv, "client_name", None) or "Kunde", 60)
        # H = credit on revenue (Haben), debit implied on receivables via Gegenkonto
        line = (
            f"{_money(amount)};H;EUR;;;;"
            f"{account_revenue};{account_receivable};;"
            f"{belegdatum};{belegfeld1};;;"
            f"{text};;;;;;\n"
        )
        lines.append(line)

    return "".join(lines)
