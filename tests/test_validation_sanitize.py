"""Tests for sanitize_input: strip tags without double-escaping plain text.

Regression: bleach.clean(tags=[], strip=True) entity-escaped surviving text
("&" -> "&amp;"), so web-UI writes stored double-escaped data that raw API
consumers (extension, mobile) displayed literally.
"""

import pytest

from app.utils.validation import sanitize_input


def test_preserves_plain_ampersand():
    assert sanitize_input("Error Handling & Security Improvements") == "Error Handling & Security Improvements"


def test_preserves_umlauts_and_punctuation():
    text = "Referenzen & Über uns Page Design, <2026>"
    assert sanitize_input(text) == "Referenzen & Über uns Page Design, <2026>"


def test_strips_html_tags():
    # bleach strips the tags; text between them remains (inert plain text)
    assert sanitize_input("<script>alert(1)</script>hello") == "alert(1)hello"
    assert sanitize_input("<b>bold</b> text") == "bold text"


def test_decodes_entities_typed_as_text_to_inert_plain_text():
    # Entities typed by the user decode to plain text; output encoding
    # (Jinja auto-escape) keeps that inert.
    assert sanitize_input("AT &amp; T") == "AT & T"
    assert sanitize_input("&lt;b&gt;not bold&lt;/b&gt;") == "<b>not bold</b>"


def test_max_length_still_truncates():
    assert sanitize_input("abcdefghij", max_length=5) == "abcde"


def test_umlaut_entity_from_legacy_data_decodes_once():
    assert sanitize_input("Kabel &amp; Stecker") == "Kabel & Stecker"

