"""Tests for PEPPOL participant identifier validation."""
import pytest

from app.integrations.peppol_identifiers import (
    PeppolIdentifierError,
    validate_endpoint_id,
    validate_participant_identifiers,
    validate_scheme_id,
)


@pytest.mark.unit
def test_validate_scheme_id_accepts_numeric():
    assert validate_scheme_id("0088") == "0088"
    assert validate_scheme_id("9915") == "9915"
    assert validate_scheme_id(" 0099 ") == "0099"


@pytest.mark.unit
def test_validate_scheme_id_rejects_empty():
    with pytest.raises(PeppolIdentifierError) as exc:
        validate_scheme_id("")
    assert "required" in str(exc.value).lower()
    with pytest.raises(PeppolIdentifierError):
        validate_scheme_id(None)


@pytest.mark.unit
def test_validate_endpoint_id_accepts_valid():
    assert validate_endpoint_id("1234567890123") == "1234567890123"
    assert validate_endpoint_id("9915:BE0123456789") == "9915:BE0123456789"
    assert validate_endpoint_id(" 0088:12345 ") == "0088:12345"


@pytest.mark.unit
def test_validate_endpoint_id_rejects_empty():
    with pytest.raises(PeppolIdentifierError) as exc:
        validate_endpoint_id("")
    assert "required" in str(exc.value).lower()


@pytest.mark.unit
def test_validate_participant_identifiers_roundtrip():
    (s_ep, s_sch), (r_ep, r_sch) = validate_participant_identifiers(
        "9915:BE111", "9915", "0088:1234567890123", "0088"
    )
    assert s_ep == "9915:BE111"
    assert s_sch == "9915"
    assert r_ep == "0088:1234567890123"
    assert r_sch == "0088"


@pytest.mark.unit
def test_validate_participant_identifiers_rejects_invalid_sender():
    with pytest.raises(PeppolIdentifierError):
        validate_participant_identifiers("", "9915", "0088:123", "0088")
    with pytest.raises(PeppolIdentifierError):
        validate_participant_identifiers("9915:BE", "", "0088:123", "0088")
