"""
Embedded Liberation fonts for PDF/A-compliant invoice PDFs.

ReportLab's base-14 fonts (Helvetica, Times-Roman, Courier) are not embedded
in the PDF stream, which violates PDF/A. Liberation fonts are metric-compatible
replacements (SIL OFL) that are registered as TrueType and fully embedded.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

_FONTS_DIR = Path(__file__).resolve().parent.parent / "resources" / "fonts"
_REGISTERED = False

# Internal registered names (used in PDF content streams)
LIBERATION_SANS = "LiberationSans"
LIBERATION_SANS_BOLD = "LiberationSans-Bold"
LIBERATION_SANS_ITALIC = "LiberationSans-Italic"
LIBERATION_SANS_BOLD_ITALIC = "LiberationSans-BoldItalic"
LIBERATION_SERIF = "LiberationSerif"
LIBERATION_SERIF_BOLD = "LiberationSerif-Bold"
LIBERATION_SERIF_ITALIC = "LiberationSerif-Italic"
LIBERATION_SERIF_BOLD_ITALIC = "LiberationSerif-BoldItalic"
LIBERATION_MONO = "LiberationMono"
LIBERATION_MONO_BOLD = "LiberationMono-Bold"
LIBERATION_MONO_ITALIC = "LiberationMono-Italic"
LIBERATION_MONO_BOLD_ITALIC = "LiberationMono-BoldItalic"

# Map ReportLab / CSS-style base-14 names to Liberation equivalents
_FONT_MAP: Dict[str, str] = {
    "Helvetica": LIBERATION_SANS,
    "Helvetica-Bold": LIBERATION_SANS_BOLD,
    "Helvetica-Oblique": LIBERATION_SANS_ITALIC,
    "Helvetica-BoldOblique": LIBERATION_SANS_BOLD_ITALIC,
    "Times-Roman": LIBERATION_SERIF,
    "Times-Bold": LIBERATION_SERIF_BOLD,
    "Times-Italic": LIBERATION_SERIF_ITALIC,
    "Times-BoldItalic": LIBERATION_SERIF_BOLD_ITALIC,
    "Courier": LIBERATION_MONO,
    "Courier-Bold": LIBERATION_MONO_BOLD,
    "Courier-Oblique": LIBERATION_MONO_ITALIC,
    "Courier-BoldOblique": LIBERATION_MONO_BOLD_ITALIC,
    # Also map Liberation names to themselves for idempotency
    LIBERATION_SANS: LIBERATION_SANS,
    LIBERATION_SANS_BOLD: LIBERATION_SANS_BOLD,
    LIBERATION_SANS_ITALIC: LIBERATION_SANS_ITALIC,
    LIBERATION_SANS_BOLD_ITALIC: LIBERATION_SANS_BOLD_ITALIC,
    LIBERATION_SERIF: LIBERATION_SERIF,
    LIBERATION_SERIF_BOLD: LIBERATION_SERIF_BOLD,
    LIBERATION_SERIF_ITALIC: LIBERATION_SERIF_ITALIC,
    LIBERATION_SERIF_BOLD_ITALIC: LIBERATION_SERIF_BOLD_ITALIC,
    LIBERATION_MONO: LIBERATION_MONO,
    LIBERATION_MONO_BOLD: LIBERATION_MONO_BOLD,
    LIBERATION_MONO_ITALIC: LIBERATION_MONO_ITALIC,
    LIBERATION_MONO_BOLD_ITALIC: LIBERATION_MONO_BOLD_ITALIC,
}

_FONT_FILES: Dict[str, str] = {
    LIBERATION_SANS: "LiberationSans-Regular.ttf",
    LIBERATION_SANS_BOLD: "LiberationSans-Bold.ttf",
    LIBERATION_SANS_ITALIC: "LiberationSans-Italic.ttf",
    LIBERATION_SANS_BOLD_ITALIC: "LiberationSans-BoldItalic.ttf",
    LIBERATION_SERIF: "LiberationSerif-Regular.ttf",
    LIBERATION_SERIF_BOLD: "LiberationSerif-Bold.ttf",
    LIBERATION_SERIF_ITALIC: "LiberationSerif-Italic.ttf",
    LIBERATION_SERIF_BOLD_ITALIC: "LiberationSerif-BoldItalic.ttf",
    LIBERATION_MONO: "LiberationMono-Regular.ttf",
    LIBERATION_MONO_BOLD: "LiberationMono-Bold.ttf",
    LIBERATION_MONO_ITALIC: "LiberationMono-Italic.ttf",
    LIBERATION_MONO_BOLD_ITALIC: "LiberationMono-BoldItalic.ttf",
}


def ensure_pdf_fonts_registered() -> bool:
    """Register Liberation TTF fonts with ReportLab (idempotent). Returns True on success."""
    global _REGISTERED
    if _REGISTERED:
        return True

    try:
        for name, filename in _FONT_FILES.items():
            path = _FONTS_DIR / filename
            if not path.is_file():
                logger.warning("Liberation font file missing: %s", path)
                return False
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(path)))

        pdfmetrics.registerFontFamily(
            LIBERATION_SANS,
            normal=LIBERATION_SANS,
            bold=LIBERATION_SANS_BOLD,
            italic=LIBERATION_SANS_ITALIC,
            boldItalic=LIBERATION_SANS_BOLD_ITALIC,
        )
        pdfmetrics.registerFontFamily(
            LIBERATION_SERIF,
            normal=LIBERATION_SERIF,
            bold=LIBERATION_SERIF_BOLD,
            italic=LIBERATION_SERIF_ITALIC,
            boldItalic=LIBERATION_SERIF_BOLD_ITALIC,
        )
        pdfmetrics.registerFontFamily(
            LIBERATION_MONO,
            normal=LIBERATION_MONO,
            bold=LIBERATION_MONO_BOLD,
            italic=LIBERATION_MONO_ITALIC,
            boldItalic=LIBERATION_MONO_BOLD_ITALIC,
        )
        _REGISTERED = True
        return True
    except Exception as e:
        logger.warning("Failed to register Liberation fonts: %s", e)
        return False


def resolve_font(name: Optional[str]) -> str:
    """
    Map a base-14 or CSS font name to an embedded Liberation font.

    Falls back to LiberationSans if the name is unknown. Ensures fonts are
    registered before returning.
    """
    ensure_pdf_fonts_registered()
    if not name:
        return LIBERATION_SANS
    mapped = _FONT_MAP.get(name) or _FONT_MAP.get(name.strip())
    if mapped:
        return mapped
    # Case-insensitive fallback for common variants
    lower = name.strip().lower()
    for key, val in _FONT_MAP.items():
        if key.lower() == lower:
            return val
    # Heuristic: bold/italic substrings
    if "courier" in lower or "mono" in lower:
        if "bold" in lower and ("italic" in lower or "oblique" in lower):
            return LIBERATION_MONO_BOLD_ITALIC
        if "bold" in lower:
            return LIBERATION_MONO_BOLD
        if "italic" in lower or "oblique" in lower:
            return LIBERATION_MONO_ITALIC
        return LIBERATION_MONO
    if "times" in lower or "serif" in lower:
        if "bold" in lower and ("italic" in lower or "oblique" in lower):
            return LIBERATION_SERIF_BOLD_ITALIC
        if "bold" in lower:
            return LIBERATION_SERIF_BOLD
        if "italic" in lower or "oblique" in lower:
            return LIBERATION_SERIF_ITALIC
        return LIBERATION_SERIF
    # Default to sans
    if "bold" in lower and ("italic" in lower or "oblique" in lower):
        return LIBERATION_SANS_BOLD_ITALIC
    if "bold" in lower:
        return LIBERATION_SANS_BOLD
    if "italic" in lower or "oblique" in lower:
        return LIBERATION_SANS_ITALIC
    return LIBERATION_SANS
