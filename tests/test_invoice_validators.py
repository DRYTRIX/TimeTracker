"""Tests for invoice validators (UBL, CII, veraPDF)."""
import pytest

from app.utils.invoice_validators import (
    validate_ubl_wellformed,
    validate_ubl_peppol_bis3,
    validate_cii_wellformed,
    validate_cii_en16931,
)


# ---- UBL well-formedness ----

@pytest.mark.unit
def test_validate_ubl_wellformed_accepts_valid_invoice():
    ubl = '<?xml version="1.0"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"><ID>INV-001</ID></Invoice>'
    passed, msgs = validate_ubl_wellformed(ubl)
    assert passed is True
    assert msgs == []


@pytest.mark.unit
def test_validate_ubl_wellformed_rejects_invalid_xml():
    passed, msgs = validate_ubl_wellformed("<bad>")
    assert passed is False
    assert len(msgs) >= 1


@pytest.mark.unit
def test_validate_ubl_wellformed_rejects_non_invoice_root():
    ubl = '<?xml version="1.0"?><NotInvoice xmlns="urn:test"><x/></NotInvoice>'
    passed, msgs = validate_ubl_wellformed(ubl)
    assert passed is False
    assert "Invoice" in msgs[0]


# ---- UBL Peppol BIS 3.0 structural validation ----

def _minimal_peppol_ubl() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0</cbc:CustomizationID>
  <cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>
  <cbc:ID>INV-001</cbc:ID>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:IssueDate>2024-01-15</cbc:IssueDate>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cbc:BuyerReference>PO-12345</cbc:BuyerReference>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cbc:EndpointID schemeID="9915">BE0123456789</cbc:EndpointID>
      <cac:PartyName><cbc:Name>Seller</cbc:Name></cac:PartyName>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cbc:EndpointID schemeID="0088">1234567890123</cbc:EndpointID>
      <cac:PartyName><cbc:Name>Buyer</cbc:Name></cac:PartyName>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:PayableAmount currencyID="EUR">100.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="C62">1.00</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cac:Item><cbc:Name>Service</cbc:Name></cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">100.00</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
</Invoice>"""


@pytest.mark.unit
def test_validate_ubl_peppol_bis3_accepts_valid():
    passed, issues = validate_ubl_peppol_bis3(_minimal_peppol_ubl())
    assert passed is True, f"Unexpected issues: {issues}"
    assert issues == []


@pytest.mark.unit
def test_validate_ubl_peppol_bis3_detects_missing_buyer_reference():
    ubl = _minimal_peppol_ubl().replace(
        "<cbc:BuyerReference>PO-12345</cbc:BuyerReference>", ""
    )
    passed, issues = validate_ubl_peppol_bis3(ubl)
    assert passed is False
    assert any("BuyerReference" in i for i in issues)


@pytest.mark.unit
def test_validate_ubl_peppol_bis3_detects_missing_endpoint():
    ubl = _minimal_peppol_ubl().replace(
        '<cbc:EndpointID schemeID="9915">BE0123456789</cbc:EndpointID>',
        "",
        1,
    )
    passed, issues = validate_ubl_peppol_bis3(ubl)
    assert passed is False
    assert any("EndpointID" in i for i in issues)


@pytest.mark.unit
def test_validate_ubl_peppol_bis3_detects_missing_lines():
    ubl = _minimal_peppol_ubl()
    # Remove InvoiceLine section
    start = ubl.index("<cac:InvoiceLine>")
    end = ubl.index("</cac:InvoiceLine>") + len("</cac:InvoiceLine>")
    ubl = ubl[:start] + ubl[end:]
    passed, issues = validate_ubl_peppol_bis3(ubl)
    assert passed is False
    assert any("InvoiceLine" in i for i in issues)


@pytest.mark.unit
def test_validate_ubl_peppol_bis3_detects_missing_unitcode():
    ubl = _minimal_peppol_ubl().replace('unitCode="C62"', "")
    passed, issues = validate_ubl_peppol_bis3(ubl)
    assert passed is False
    assert any("unitCode" in i for i in issues)


# ---- CII well-formedness ----

@pytest.mark.unit
def test_validate_cii_wellformed_accepts_valid():
    cii = '<?xml version="1.0"?><rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"><x/></rsm:CrossIndustryInvoice>'
    passed, msgs = validate_cii_wellformed(cii)
    assert passed is True


@pytest.mark.unit
def test_validate_cii_wellformed_rejects_ubl():
    ubl = '<?xml version="1.0"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"><ID>1</ID></Invoice>'
    passed, msgs = validate_cii_wellformed(ubl)
    assert passed is False
    assert "CrossIndustryInvoice" in msgs[0]


@pytest.mark.unit
def test_validate_cii_wellformed_rejects_invalid_xml():
    passed, msgs = validate_cii_wellformed("<not valid")
    assert passed is False


# ---- CII EN 16931 structural validation ----

def _minimal_cii_en16931() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
    xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext>
    <ram:GuidelineSpecifiedDocumentContextParameter>
      <ram:ID>urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:en16931</ram:ID>
    </ram:GuidelineSpecifiedDocumentContextParameter>
  </rsm:ExchangedDocumentContext>
  <rsm:ExchangedDocument>
    <ram:ID>INV-001</ram:ID>
    <ram:TypeCode>380</ram:TypeCode>
    <ram:IssueDateTime>
      <udt:DateTimeString format="102">20240115</udt:DateTimeString>
    </ram:IssueDateTime>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:ApplicableHeaderTradeAgreement>
      <ram:SellerTradeParty>
        <ram:Name>Seller Company</ram:Name>
      </ram:SellerTradeParty>
      <ram:BuyerTradeParty>
        <ram:Name>Buyer Company</ram:Name>
      </ram:BuyerTradeParty>
    </ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeDelivery/>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
      <ram:ApplicableTradeTax>
        <ram:CalculatedAmount>0.00</ram:CalculatedAmount>
        <ram:TypeCode>VAT</ram:TypeCode>
        <ram:BasisAmount>100.00</ram:BasisAmount>
        <ram:CategoryCode>Z</ram:CategoryCode>
        <ram:RateApplicablePercent>0.00</ram:RateApplicablePercent>
      </ram:ApplicableTradeTax>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:LineTotalAmount>100.00</ram:LineTotalAmount>
        <ram:TaxBasisTotalAmount>100.00</ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount currencyID="EUR">0.00</ram:TaxTotalAmount>
        <ram:GrandTotalAmount>100.00</ram:GrandTotalAmount>
        <ram:DuePayableAmount>100.00</ram:DuePayableAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
    <ram:IncludedSupplyChainTradeLineItem>
      <ram:AssociatedDocumentLineDocument>
        <ram:LineID>1</ram:LineID>
      </ram:AssociatedDocumentLineDocument>
      <ram:SpecifiedTradeProduct>
        <ram:Name>Service</ram:Name>
      </ram:SpecifiedTradeProduct>
      <ram:SpecifiedLineTradeAgreement>
        <ram:NetPriceProductTradePrice>
          <ram:ChargeAmount>100.00</ram:ChargeAmount>
        </ram:NetPriceProductTradePrice>
      </ram:SpecifiedLineTradeAgreement>
      <ram:SpecifiedLineTradeDelivery>
        <ram:BilledQuantity unitCode="C62">1.00</ram:BilledQuantity>
      </ram:SpecifiedLineTradeDelivery>
      <ram:SpecifiedLineTradeSettlement>
        <ram:ApplicableTradeTax>
          <ram:TypeCode>VAT</ram:TypeCode>
          <ram:CategoryCode>Z</ram:CategoryCode>
          <ram:RateApplicablePercent>0.00</ram:RateApplicablePercent>
        </ram:ApplicableTradeTax>
        <ram:SpecifiedTradeSettlementLineMonetarySummation>
          <ram:LineTotalAmount>100.00</ram:LineTotalAmount>
        </ram:SpecifiedTradeSettlementLineMonetarySummation>
      </ram:SpecifiedLineTradeSettlement>
    </ram:IncludedSupplyChainTradeLineItem>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""


@pytest.mark.unit
def test_validate_cii_en16931_accepts_valid():
    passed, issues = validate_cii_en16931(_minimal_cii_en16931())
    assert passed is True, f"Unexpected issues: {issues}"


@pytest.mark.unit
def test_validate_cii_en16931_detects_missing_seller():
    cii = _minimal_cii_en16931().replace(
        "<ram:SellerTradeParty>\n        <ram:Name>Seller Company</ram:Name>\n      </ram:SellerTradeParty>",
        "",
    )
    passed, issues = validate_cii_en16931(cii)
    assert passed is False
    assert any("Seller" in i for i in issues)


@pytest.mark.unit
def test_validate_cii_en16931_detects_missing_document_id():
    cii = _minimal_cii_en16931().replace("<ram:ID>INV-001</ram:ID>", "")
    passed, issues = validate_cii_en16931(cii)
    assert passed is False
    assert any("ID" in i or "Invoice number" in i for i in issues)


@pytest.mark.unit
def test_validate_cii_en16931_detects_missing_line_items():
    cii = _minimal_cii_en16931()
    start = cii.index("<ram:IncludedSupplyChainTradeLineItem>")
    end = cii.index("</ram:IncludedSupplyChainTradeLineItem>") + len(
        "</ram:IncludedSupplyChainTradeLineItem>"
    )
    cii = cii[:start] + cii[end:]
    passed, issues = validate_cii_en16931(cii)
    assert passed is False
    assert any("LineItem" in i or "line" in i.lower() for i in issues)


@pytest.mark.unit
def test_validate_cii_en16931_detects_missing_grand_total():
    cii = _minimal_cii_en16931().replace(
        "<ram:GrandTotalAmount>100.00</ram:GrandTotalAmount>", ""
    )
    passed, issues = validate_cii_en16931(cii)
    assert passed is False
    assert any("GrandTotal" in i for i in issues)
