"""FatturaPA 1.2 XML export tests."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.utils.fatturapa import (
    FATTURAPA_VERSION_FPA,
    FATTURAPA_VERSION_FPR,
    build_fatturapa_filename,
    build_fatturapa_xml,
    determine_formato,
    progressivo_from_id,
    resolve_codice_destinatario,
    resolve_natura,
    validate_fatturapa_ready,
)

FIXTURES = Path(__file__).parent / "fixtures" / "fatturapa"
XSD_PATH = FIXTURES / "Schema_del_file_xml_FatturaPA_versione_1.2.1.xsd"


def _settings(**kwargs):
    base = dict(
        company_name="Acme Srl",
        company_street="Via Roma 1",
        company_postcode="20121",
        company_city="Milano",
        company_country="IT",
        company_provincia="MI",
        company_tax_id="IT01234567890",
        company_codice_fiscale="01234567890",
        company_regime_fiscale="RF01",
        company_iban="IT60X0542811101000000123456",
        company_bic="BPMOIT22XXX",
        company_address="Via Roma 1, Milano",
        company_email="billing@acme.it",
        company_phone="+39 02 123456",
        sdi_transmitter_id="",
        invoices_default_vat_category="S",
        invoices_default_vat_exemption_reason="",
        invoices_default_vat_exemption_code="",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _client(**kwargs):
    base = dict(
        name="Cliente Spa",
        street="Corso Italia 10",
        postcode="00187",
        city="Roma",
        country="IT",
        provincia="RM",
        vat_id="IT09876543210",
        codice_fiscale="09876543210",
        address="Corso Italia 10",
        email="acquisti@cliente.it",
        phone="+39 06 123456",
        sdi_codice_destinatario="ABC1234",
        pec_email="",
    )
    base.update(kwargs)
    ns = SimpleNamespace(**base)
    ns.get_custom_field = lambda key, default="": default
    return ns


def _invoice(**kwargs):
    price = Decimal("100.00")
    item = SimpleNamespace(description="Consulenza", quantity=1, unit_price=price, total_amount=price)
    base = dict(
        id=42,
        invoice_number="FT-2026-1",
        issue_date=date(2026, 11, 7),
        due_date=date(2026, 12, 7),
        currency_code="EUR",
        subtotal=price,
        tax_rate=Decimal("22"),
        tax_amount=Decimal("22.00"),
        total_amount=Decimal("122.00"),
        notes=None,
        items=[item],
        expenses=[],
        extra_goods=[],
        client_name="Cliente Spa",
        vat_category=None,
        vat_exemption_code=None,
        vat_exemption_reason=None,
        cig=None,
        cup=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_progressivo_from_id_base36_padded():
    assert progressivo_from_id(1) == "00001"
    assert len(progressivo_from_id(12345)) == 5


def test_determine_formato_pa_vs_b2b():
    assert determine_formato(_client(sdi_codice_destinatario="UFXYZ1")) == FATTURAPA_VERSION_FPA
    assert determine_formato(_client(sdi_codice_destinatario="ABC1234")) == FATTURAPA_VERSION_FPR


def test_resolve_codice_pec_and_foreign():
    code, pec = resolve_codice_destinatario(_client(sdi_codice_destinatario="", pec_email="a@pec.it"))
    assert code == "0000000"
    assert pec == "a@pec.it"
    code, pec = resolve_codice_destinatario(_client(sdi_codice_destinatario="", pec_email="", country="DE"))
    assert code == "XXXXXXX"
    assert pec is None


def test_validate_fails_without_recipient():
    issues = validate_fatturapa_ready(
        _invoice(), _settings(), _client(sdi_codice_destinatario="", pec_email="")
    )
    assert any("Codice Destinatario" in msg or "PEC" in msg for msg in issues)


def test_validate_fails_without_provincia_for_it():
    issues = validate_fatturapa_ready(_invoice(), _settings(company_provincia=""), _client())
    assert any("provincia" in msg.lower() for msg in issues)


def test_build_fpr12_structure():
    xml, filename, sha = build_fatturapa_xml(_invoice(), _settings(), _client(), "0002A")
    assert "versione=\"FPR12\"" in xml or "versione='FPR12'" in xml
    assert "FatturaElettronicaHeader" in xml
    assert "CedentePrestatore" in xml
    assert "CessionarioCommittente" in xml
    assert "DettaglioLinee" in xml
    assert "DatiRiepilogo" in xml
    assert "ABC1234" in xml
    assert "Consulenza" in xml
    assert filename.startswith("IT") and filename.endswith("_0002A.xml")
    assert len(sha) == 64


def test_build_fpa12_with_cig_cup():
    client = _client(sdi_codice_destinatario="UFABC1")
    inv = _invoice(cig="Z1234567890", cup="J12C3400010001")
    xml, _fn, _sha = build_fatturapa_xml(inv, _settings(), client, "00001")
    assert "versione=\"FPA12\"" in xml or "versione='FPA12'" in xml
    assert "CodiceCIG" in xml
    assert "Z1234567890" in xml
    assert "CodiceCUP" in xml


def test_pec_fallback_xml():
    client = _client(sdi_codice_destinatario="", pec_email="cliente@pec.example.it")
    xml, _fn, _sha = build_fatturapa_xml(_invoice(), _settings(), client, "00001")
    assert "0000000" in xml
    assert "PECDestinatario" in xml
    assert "cliente@pec.example.it" in xml


def test_foreign_buyer_uses_xxxxxxx():
    client = _client(
        sdi_codice_destinatario="",
        pec_email="",
        country="DE",
        provincia="",
        vat_id="DE123456789",
        codice_fiscale="",
        postcode="10115",
    )
    # Foreign buyers don't need Italian provincia
    settings = _settings()
    issues = validate_fatturapa_ready(_invoice(), settings, client)
    assert not any("provincia" in m.lower() and "Client" in m for m in issues)
    xml, _fn, _sha = build_fatturapa_xml(_invoice(), settings, client, "00001")
    assert "XXXXXXX" in xml
    assert ">00000<" in xml  # foreign CAP


def test_natura_mapping_zero_rate():
    inv = _invoice(tax_rate=Decimal("0"), tax_amount=Decimal("0"), total_amount=Decimal("100.00"), vat_category="E")
    settings = _settings()
    assert resolve_natura(inv, settings, Decimal("0")) == "N4"
    xml, _fn, _sha = build_fatturapa_xml(inv, settings, _client(), "00001")
    assert "<Natura>N4</Natura>" in xml


def test_natura_from_exemption_code():
    inv = _invoice(
        tax_rate=Decimal("0"),
        tax_amount=Decimal("0"),
        total_amount=Decimal("100.00"),
        vat_exemption_code="N3.1",
        vat_exemption_reason="Export art. 8",
    )
    assert resolve_natura(inv, _settings(), Decimal("0")) == "N3.1"
    xml, _fn, _sha = build_fatturapa_xml(inv, _settings(), _client(), "00001")
    assert "<Natura>N3.1</Natura>" in xml
    assert "Export art. 8" in xml


def test_filename_format():
    assert build_fatturapa_filename("01234567890", "00001") == "IT01234567890_00001.xml"


def test_xsd_validation_fpr12():
    etree = pytest.importorskip("lxml.etree")
    if not XSD_PATH.exists():
        pytest.skip("FatturaPA XSD fixture missing")

    xml, _fn, _sha = build_fatturapa_xml(_invoice(), _settings(), _client(), "00001")

    # Rewrite remote xmldsig import to local fixture for offline validation
    xsd_text = XSD_PATH.read_text(encoding="utf-8-sig")
    local_dsig = (FIXTURES / "xmldsig-core-schema.xsd").as_uri()
    xsd_text = xsd_text.replace(
        'schemaLocation="http://www.w3.org/TR/2002/REC-xmldsig-core-20020212/xmldsig-core-schema.xsd"',
        f'schemaLocation="{local_dsig}"',
    )
    schema_doc = etree.fromstring(xsd_text.encode("utf-8"))
    schema = etree.XMLSchema(schema_doc)
    doc = etree.fromstring(xml.encode("utf-8"))
    if not schema.validate(doc):
        pytest.fail(f"XSD validation failed: {schema.error_log.filter_from_errors()}")
