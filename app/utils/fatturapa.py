"""
FatturaPA 1.2 XML export helpers (FPR12 B2B / FPA12 public administration).

Builds Italian electronic invoices under the Agenzia delle Entrate schema.
Transmission to SDI is handled separately via SdiService + GenericSdiTransport.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

FATTURAPA_NS = "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
FATTURAPA_VERSION_FPR = "FPR12"
FATTURAPA_VERSION_FPA = "FPA12"

# Map EN 16931 / Factur-X VAT categories to FatturaPA Natura codes (0% lines)
_VAT_CATEGORY_TO_NATURA = {
    "Z": "N2.2",
    "O": "N2.2",
    "E": "N4",
    "AE": "N6.9",
    "K": "N3.2",
    "G": "N3.1",
}

_NATURA_RE = re.compile(r"^N\d(\.\d+)?$")
_BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def fatturapa_export_available() -> bool:
    return True


def _strip(v: Any) -> str:
    return (v or "").strip() if v is not None else ""


def _money(value: Any, places: int = 2) -> str:
    q = Decimal("1").scaleb(-places)
    try:
        d = Decimal(str(value if value is not None else 0))
    except Exception:
        d = Decimal("0")
    return str(d.quantize(q, rounding=ROUND_HALF_UP))


def _unit_price(value: Any) -> str:
    """Amount8DecimalType: require at least 2 decimal places, up to 8."""
    raw = _money(value, places=8)
    # Trim trailing zeros but keep at least two fractional digits (XSD pattern).
    if "." in raw:
        whole, frac = raw.split(".", 1)
        frac = frac.rstrip("0").ljust(2, "0")
        return f"{whole}.{frac}"
    return f"{raw}.00"


def _qty(value: Any) -> str:
    """QuantityType: [0-9]{1,12}\\.[0-9]{2,8}"""
    return _unit_price(value)


def progressivo_from_id(n: int) -> str:
    """Encode a positive integer as a 5-character base36 ProgressivoInvio."""
    if n < 1:
        n = 1
    chars: List[str] = []
    x = n
    while x > 0:
        chars.append(_BASE36[x % 36])
        x //= 36
    s = "".join(reversed(chars)) or "1"
    return s.zfill(5)[-5:]


def determine_formato(client: Any) -> str:
    """FPA12 for 6-char PA codes, otherwise FPR12 (B2B)."""
    code = _strip(getattr(client, "sdi_codice_destinatario", None)).upper()
    if len(code) == 6 and code not in ("000000", "XXXXXX"):
        return FATTURAPA_VERSION_FPA
    return FATTURAPA_VERSION_FPR


def resolve_codice_destinatario(client: Any) -> Tuple[str, Optional[str]]:
    """
    Return (CodiceDestinatario, PECDestinatario or None).
    - Explicit SDI code when set
    - 0000000 + PEC when only PEC is available (B2B)
    - XXXXXXX for foreign buyers without an Italian SDI code
    """
    code = _strip(getattr(client, "sdi_codice_destinatario", None)).upper()
    pec = _strip(getattr(client, "pec_email", None))
    country = _strip(getattr(client, "country", None)).upper() or "IT"

    if code:
        return code, pec if code == "0000000" and pec else (None if code != "0000000" else pec or None)

    if country and country != "IT":
        return "XXXXXXX", None

    if pec:
        return "0000000", pec

    return "", None


def _vat_category(invoice: Any, settings: Any) -> str:
    cat = _strip(getattr(invoice, "vat_category", None))
    if cat:
        return cat.upper()
    return (_strip(getattr(settings, "invoices_default_vat_category", None)) or "S").upper()


def _exemption_code(invoice: Any, settings: Any) -> str:
    code = _strip(getattr(invoice, "vat_exemption_code", None))
    if not code:
        code = _strip(getattr(settings, "invoices_default_vat_exemption_code", None))
    return code


def _exemption_reason(invoice: Any, settings: Any) -> str:
    reason = _strip(getattr(invoice, "vat_exemption_reason", None))
    if not reason:
        reason = _strip(getattr(settings, "invoices_default_vat_exemption_reason", None))
    return reason


def resolve_natura(invoice: Any, settings: Any, tax_rate: Decimal) -> Optional[str]:
    """Return Natura code for 0% lines, else None."""
    if tax_rate > 0:
        return None
    raw = _exemption_code(invoice, settings)
    if raw and _NATURA_RE.match(raw):
        return raw
    cat = _vat_category(invoice, settings)
    if cat == "S":
        # Standard category with 0% is unusual; treat as non-taxable
        return "N2.2"
    return _VAT_CATEGORY_TO_NATURA.get(cat, "N2.2")


def _italian_id_parts(tax_id: str, codice_fiscale: str = "") -> Tuple[str, str, Optional[str]]:
    """
    Return (IdPaese, IdCodice for IdFiscaleIVA, CodiceFiscale or None).
    Prefer P.IVA (11 digits) for IdFiscaleIVA; CF goes in CodiceFiscale.
    """
    vat = re.sub(r"[\s.]", "", tax_id or "")
    cf = re.sub(r"[\s.]", "", codice_fiscale or "").upper()

    country = "IT"
    digits = vat
    if len(vat) >= 3 and vat[:2].isalpha():
        country = vat[:2].upper()
        digits = vat[2:]

    id_codice = digits or None
    codice_fiscale_out = cf or None

    # If only CF provided (16 chars alphanumeric), use it as CodiceFiscale and
    # for sole traders without P.IVA put CF into IdCodice as well when needed.
    if not id_codice and cf:
        if len(cf) == 11 and cf.isdigit():
            id_codice = cf
            codice_fiscale_out = None
        else:
            id_codice = cf

    return country, id_codice or "", codice_fiscale_out


def validate_fatturapa_ready(invoice: Any, settings: Any, client: Any) -> List[str]:
    """Return human-readable messages for missing mandatory FatturaPA fields."""
    issues: List[str] = []

    if not _strip(getattr(settings, "company_name", None)):
        issues.append("Settings: company name is required (seller).")
    if not (
        _strip(getattr(settings, "company_street", None)) or _strip(getattr(settings, "company_address", None))
    ):
        issues.append("Settings: company street or address is required.")
    if not _strip(getattr(settings, "company_postcode", None)):
        issues.append("Settings: company postcode (CAP) is required.")
    if not _strip(getattr(settings, "company_city", None)):
        issues.append("Settings: company city is required.")
    country = _strip(getattr(settings, "company_country", None)).upper()
    if not country:
        issues.append("Settings: company country (ISO 2) is required.")
    elif country == "IT" and not _strip(getattr(settings, "company_provincia", None)):
        issues.append("Settings: company provincia (2 letters) is required for Italian sellers.")
    if not _strip(getattr(settings, "company_regime_fiscale", None)):
        issues.append("Settings: RegimeFiscale is required (e.g. RF01).")

    tax_id = _strip(getattr(settings, "company_tax_id", None))
    cf = _strip(getattr(settings, "company_codice_fiscale", None))
    if not tax_id and not cf:
        issues.append("Settings: company VAT ID (Partita IVA) or Codice Fiscale is required.")

    if client is None:
        issues.append("Invoice must be linked to a client.")
    else:
        if not _strip(getattr(client, "name", None)):
            issues.append("Client: name is required.")
        if not (_strip(getattr(client, "street", None)) or _strip(getattr(client, "address", None))):
            issues.append("Client: street or address is required.")
        if not _strip(getattr(client, "postcode", None)):
            issues.append("Client: postcode (CAP) is required.")
        if not _strip(getattr(client, "city", None)):
            issues.append("Client: city is required.")
        c_country = _strip(getattr(client, "country", None)).upper()
        if not c_country:
            issues.append("Client: country (ISO 2) is required.")
        elif c_country == "IT" and not _strip(getattr(client, "provincia", None)):
            issues.append("Client: provincia (2 letters) is required for Italian buyers.")

        c_vat = _strip(getattr(client, "vat_id", None))
        if not c_vat and hasattr(client, "get_custom_field"):
            c_vat = _strip(client.get_custom_field("vat_id", "") or client.get_custom_field("tax_id", ""))
        c_cf = _strip(getattr(client, "codice_fiscale", None))
        if not c_vat and not c_cf:
            issues.append("Client: VAT ID (Partita IVA) or Codice Fiscale is required.")

        code, pec = resolve_codice_destinatario(client)
        if not code:
            issues.append("Client: SDI Codice Destinatario or PEC email is required.")
        formato = determine_formato(client)
        if formato == FATTURAPA_VERSION_FPA and len(code) != 6:
            issues.append("Client: public administration invoices require a 6-character Codice Destinatario.")
        if code == "0000000" and not pec:
            issues.append("Client: PEC email is required when Codice Destinatario is 0000000.")

    if not _strip(getattr(invoice, "invoice_number", None)):
        issues.append("Invoice number is required.")

    return issues


def _sub(parent: ET.Element, tag: str) -> ET.Element:
    # Local elements are unqualified (elementFormDefault=unqualified in the XSD).
    return ET.SubElement(parent, tag)


def _set_text(parent: ET.Element, tag: str, text: str) -> ET.Element:
    el = _sub(parent, tag)
    el.text = text
    return el


def _add_id_fiscale_iva(parent: ET.Element, paese: str, codice: str) -> None:
    block = _sub(parent, "IdFiscaleIVA")
    _set_text(block, "IdPaese", paese)
    _set_text(block, "IdCodice", codice)


def _add_address(
    parent: ET.Element,
    *,
    street: str,
    postcode: str,
    city: str,
    provincia: str,
    country: str,
) -> None:
    addr = _sub(parent, "Sede")
    _set_text(addr, "Indirizzo", (street or "N/A")[:60])
    nation = (country or "IT").upper()[:2]
    if nation != "IT":
        cap = "00000"
    else:
        digits = re.sub(r"\D", "", postcode or "")
        cap = digits[:5].zfill(5) if digits else "00000"
    _set_text(addr, "CAP", cap)
    _set_text(addr, "Comune", (city or "N/A")[:60])
    if nation == "IT" and provincia:
        _set_text(addr, "Provincia", provincia.upper()[:2])
    _set_text(addr, "Nazione", nation)


def _collect_lines(invoice: Any) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []
    try:
        for it in list(getattr(invoice, "items", []) or []):
            lines.append(
                {
                    "description": _strip(getattr(it, "description", None)) or "Item",
                    "quantity": getattr(it, "quantity", 1) or 1,
                    "unit_price": getattr(it, "unit_price", 0) or 0,
                    "line_total": getattr(it, "total_amount", 0) or 0,
                }
            )
    except Exception:
        pass
    try:
        expenses_rel = getattr(invoice, "expenses", None)
        for ex in list(expenses_rel) if expenses_rel is not None else []:
            desc = _strip(getattr(ex, "title", None)) or "Expense"
            if getattr(ex, "vendor", None):
                desc = f"{desc} ({ex.vendor})"
            amt = getattr(ex, "total_amount", 0) or 0
            lines.append({"description": desc, "quantity": 1, "unit_price": amt, "line_total": amt})
    except Exception:
        pass
    try:
        goods_rel = getattr(invoice, "extra_goods", None)
        for g in list(goods_rel) if goods_rel is not None else []:
            lines.append(
                {
                    "description": _strip(getattr(g, "name", None)) or "Good",
                    "quantity": getattr(g, "quantity", 1) or 1,
                    "unit_price": getattr(g, "unit_price", 0) or 0,
                    "line_total": getattr(g, "total_amount", 0) or 0,
                }
            )
    except Exception:
        pass
    if not lines:
        # Fallback single line from invoice totals
        subtotal = getattr(invoice, "subtotal", None) or getattr(invoice, "total_amount", 0) or 0
        lines.append(
            {
                "description": _strip(getattr(invoice, "notes", None)) or "Services",
                "quantity": 1,
                "unit_price": subtotal,
                "line_total": subtotal,
            }
        )
    return lines


def _transmitter_id(settings: Any) -> str:
    tid = _strip(getattr(settings, "sdi_transmitter_id", None))
    if tid:
        # Strip country prefix if present
        if len(tid) > 2 and tid[:2].isalpha():
            return re.sub(r"[\s.]", "", tid[2:])
        return re.sub(r"[\s.]", "", tid)
    cf = _strip(getattr(settings, "company_codice_fiscale", None))
    if cf:
        return re.sub(r"[\s.]", "", cf)
    tax = _strip(getattr(settings, "company_tax_id", None))
    if tax:
        if len(tax) >= 3 and tax[:2].isalpha():
            return re.sub(r"[\s.]", "", tax[2:])
        return re.sub(r"[\s.]", "", tax)
    return "00000000000"


def build_fatturapa_filename(transmitter_id: str, progressivo: str) -> str:
    tid = re.sub(r"[^A-Za-z0-9]", "", transmitter_id or "")[:16]
    prog = (progressivo or "00001")[:10]
    return f"IT{tid}_{prog}.xml"


def build_fatturapa_xml(
    invoice: Any,
    settings: Any,
    client: Any,
    progressivo: str,
) -> Tuple[str, str, str]:
    """
    Build FatturaPA 1.2 XML.
    Returns (xml_string, filename, sha256_hex).
    Call validate_fatturapa_ready first in routes.
    """
    formato = determine_formato(client)
    codice_dest, pec_dest = resolve_codice_destinatario(client)
    transmitter = _transmitter_id(settings)
    progressivo = (progressivo or progressivo_from_id(getattr(invoice, "id", 1) or 1))[:10]

    try:
        tax_rate = Decimal(str(getattr(invoice, "tax_rate", 0) or 0))
    except Exception:
        tax_rate = Decimal("0")
    natura = resolve_natura(invoice, settings, tax_rate)
    rif_norm = _exemption_reason(invoice, settings) if natura else ""

    # Keep a named prefix (not default xmlns) so unqualified local children stay
    # in no-namespace, matching the official XSD elementFormDefault.
    ET.register_namespace("p", FATTURAPA_NS)
    root = ET.Element(f"{{{FATTURAPA_NS}}}FatturaElettronica")
    root.set("versione", formato)

    header = _sub(root, "FatturaElettronicaHeader")

    # --- DatiTrasmissione ---
    dt = _sub(header, "DatiTrasmissione")
    id_tr = _sub(dt, "IdTrasmittente")
    _set_text(id_tr, "IdPaese", "IT")
    _set_text(id_tr, "IdCodice", transmitter)
    _set_text(dt, "ProgressivoInvio", progressivo)
    _set_text(dt, "FormatoTrasmissione", formato)
    _set_text(dt, "CodiceDestinatario", codice_dest or "0000000")
    if pec_dest and (codice_dest or "") == "0000000":
        _set_text(dt, "PECDestinatario", pec_dest)

    # --- CedentePrestatore (seller) ---
    seller_vat = _strip(getattr(settings, "company_tax_id", None))
    seller_cf = _strip(getattr(settings, "company_codice_fiscale", None))
    s_paese, s_codice, s_cf = _italian_id_parts(seller_vat, seller_cf)

    cedente = _sub(header, "CedentePrestatore")
    dati_anag = _sub(cedente, "DatiAnagrafici")
    if s_codice:
        _add_id_fiscale_iva(dati_anag, s_paese, s_codice)
    if s_cf:
        _set_text(dati_anag, "CodiceFiscale", s_cf)
    anagrafica = _sub(dati_anag, "Anagrafica")
    _set_text(anagrafica, "Denominazione", _strip(getattr(settings, "company_name", None))[:80] or "Company")
    _set_text(dati_anag, "RegimeFiscale", _strip(getattr(settings, "company_regime_fiscale", None)) or "RF01")

    seller_street = _strip(getattr(settings, "company_street", None)) or _strip(
        getattr(settings, "company_address", None)
    )
    _add_address(
        cedente,
        street=seller_street,
        postcode=_strip(getattr(settings, "company_postcode", None)),
        city=_strip(getattr(settings, "company_city", None)),
        provincia=_strip(getattr(settings, "company_provincia", None)),
        country=_strip(getattr(settings, "company_country", None)) or "IT",
    )

    # --- CessionarioCommittente (buyer) ---
    buyer_vat = _strip(getattr(client, "vat_id", None))
    if not buyer_vat and hasattr(client, "get_custom_field"):
        buyer_vat = _strip(client.get_custom_field("vat_id", "") or client.get_custom_field("tax_id", ""))
    buyer_cf = _strip(getattr(client, "codice_fiscale", None))
    b_paese, b_codice, b_cf = _italian_id_parts(buyer_vat, buyer_cf)
    buyer_country = _strip(getattr(client, "country", None)).upper() or b_paese or "IT"
    if buyer_country != "IT" and not b_paese:
        b_paese = buyer_country

    cessionario = _sub(header, "CessionarioCommittente")
    c_dati = _sub(cessionario, "DatiAnagrafici")
    if b_codice:
        _add_id_fiscale_iva(c_dati, b_paese or buyer_country, b_codice)
    if b_cf:
        _set_text(c_dati, "CodiceFiscale", b_cf)
    c_anag = _sub(c_dati, "Anagrafica")
    buyer_name = _strip(getattr(client, "name", None) or getattr(invoice, "client_name", None)) or "Customer"
    _set_text(c_anag, "Denominazione", buyer_name[:80])

    buyer_street = _strip(getattr(client, "street", None)) or _strip(getattr(client, "address", None))
    _add_address(
        cessionario,
        street=buyer_street,
        postcode=_strip(getattr(client, "postcode", None)),
        city=_strip(getattr(client, "city", None)),
        provincia=_strip(getattr(client, "provincia", None)),
        country=buyer_country,
    )

    # --- Body ---
    body = _sub(root, "FatturaElettronicaBody")
    dati_gen = _sub(body, "DatiGenerali")
    dgd = _sub(dati_gen, "DatiGeneraliDocumento")
    _set_text(dgd, "TipoDocumento", "TD01")
    currency = (_strip(getattr(invoice, "currency_code", None)) or "EUR").upper()[:3]
    _set_text(dgd, "Divisa", currency)
    issue = getattr(invoice, "issue_date", None)
    issue_s = issue.isoformat() if hasattr(issue, "isoformat") else str(issue or "")[:10]
    _set_text(dgd, "Data", issue_s)
    _set_text(dgd, "Numero", _strip(getattr(invoice, "invoice_number", None))[:20])
    total = getattr(invoice, "total_amount", 0) or 0
    _set_text(dgd, "ImportoTotaleDocumento", _money(total))

    cig = _strip(getattr(invoice, "cig", None))
    cup = _strip(getattr(invoice, "cup", None))
    if cig or cup:
        ordine = _sub(dati_gen, "DatiOrdineAcquisto")
        _set_text(ordine, "IdDocumento", _strip(getattr(invoice, "invoice_number", None))[:20] or "1")
        if cig:
            _set_text(ordine, "CodiceCIG", cig[:15])
        if cup:
            _set_text(ordine, "CodiceCUP", cup[:15])

    # Line items
    beni = _sub(body, "DatiBeniServizi")
    lines = _collect_lines(invoice)
    taxable_sum = Decimal("0")
    for idx, line in enumerate(lines, start=1):
        det = _sub(beni, "DettaglioLinee")
        _set_text(det, "NumeroLinea", str(idx))
        _set_text(det, "Descrizione", str(line["description"])[:1000])
        _set_text(det, "Quantita", _qty(line["quantity"]))
        _set_text(det, "PrezzoUnitario", _unit_price(line["unit_price"]))
        line_total = Decimal(str(line["line_total"] or 0))
        taxable_sum += line_total
        _set_text(det, "PrezzoTotale", _money(line_total))
        _set_text(det, "AliquotaIVA", _money(tax_rate))
        if natura:
            _set_text(det, "Natura", natura)

    # Prefer invoice subtotal when present
    try:
        inv_sub = Decimal(str(getattr(invoice, "subtotal", None) or taxable_sum))
    except Exception:
        inv_sub = taxable_sum
    try:
        inv_tax = Decimal(str(getattr(invoice, "tax_amount", None) or 0))
    except Exception:
        inv_tax = (inv_sub * tax_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    riep = _sub(beni, "DatiRiepilogo")
    _set_text(riep, "AliquotaIVA", _money(tax_rate))
    if natura:
        _set_text(riep, "Natura", natura)
    _set_text(riep, "ImponibileImporto", _money(inv_sub))
    _set_text(riep, "Imposta", _money(inv_tax))
    _set_text(riep, "EsigibilitaIVA", "I")
    if rif_norm:
        _set_text(riep, "RiferimentoNormativo", rif_norm[:100])

    # Payment
    iban = _strip(getattr(settings, "company_iban", None))
    due = getattr(invoice, "due_date", None)
    if iban or due:
        pag = _sub(body, "DatiPagamento")
        _set_text(pag, "CondizioniPagamento", "TP02")
        det_pag = _sub(pag, "DettaglioPagamento")
        _set_text(det_pag, "ModalitaPagamento", "MP05")
        if due and hasattr(due, "isoformat"):
            _set_text(det_pag, "DataScadenzaPagamento", due.isoformat())
        _set_text(det_pag, "ImportoPagamento", _money(total))
        if iban:
            _set_text(det_pag, "IBAN", iban.replace(" ", ""))

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    xml_str = xml_bytes.decode("utf-8")

    filename = build_fatturapa_filename(transmitter, progressivo)
    sha256_hex = hashlib.sha256(xml_str.encode("utf-8")).hexdigest()
    return xml_str, filename, sha256_hex
