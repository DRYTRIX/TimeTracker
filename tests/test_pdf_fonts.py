"""Tests for embedded Liberation PDF fonts."""
import pytest


@pytest.mark.unit
def test_resolve_font_maps_base14():
    from app.utils.pdf_fonts import (
        LIBERATION_MONO,
        LIBERATION_SANS,
        LIBERATION_SANS_BOLD,
        LIBERATION_SERIF,
        ensure_pdf_fonts_registered,
        resolve_font,
    )

    assert ensure_pdf_fonts_registered() is True
    assert resolve_font("Helvetica") == LIBERATION_SANS
    assert resolve_font("Helvetica-Bold") == LIBERATION_SANS_BOLD
    assert resolve_font("Times-Roman") == LIBERATION_SERIF
    assert resolve_font("Courier") == LIBERATION_MONO
    assert resolve_font(None) == LIBERATION_SANS
