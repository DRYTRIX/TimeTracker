"""
Optional "Generated with TimeTracker" footer watermark for exported PDFs.

Drawn on every page unless the instance has an activated supporter / license key
(Settings.donate_ui_hidden via is_license_activated).
"""

from __future__ import annotations

from typing import Callable, Optional

from reportlab.lib import colors
from reportlab.lib.units import cm

from app.utils.license_utils import is_license_activated

WATERMARK_TEXT = "Generated with TimeTracker - timetracker.drytrix.com"
WATERMARK_URL = "https://timetracker.drytrix.com"
WATERMARK_COLOR = colors.HexColor("#9ca3af")
WATERMARK_FONT_SIZE = 6
WATERMARK_Y = 0.35 * cm
WATERMARK_X = 1.5 * cm


def should_draw_watermark(settings=None) -> bool:
    """Return True when the PDF watermark should be drawn (unlicensed instance)."""
    if settings is None:
        try:
            from app.models import Settings

            settings = Settings.get_settings()
        except Exception:
            # No app/DB context: default to showing the watermark.
            return True
    return not is_license_activated(settings)


def draw_watermark(canv, doc) -> None:
    """Draw a small branded footer line at the bottom-left of the page."""
    canv.saveState()
    try:
        canv.setFont("Helvetica", WATERMARK_FONT_SIZE)
        canv.setFillColor(WATERMARK_COLOR)
        canv.drawString(WATERMARK_X, WATERMARK_Y, WATERMARK_TEXT)
        text_width = canv.stringWidth(WATERMARK_TEXT, "Helvetica", WATERMARK_FONT_SIZE)
        # Clickable link covering the watermark text
        canv.linkURL(
            WATERMARK_URL,
            (WATERMARK_X, WATERMARK_Y - 1, WATERMARK_X + text_width, WATERMARK_Y + WATERMARK_FONT_SIZE),
            relative=0,
        )
    finally:
        canv.restoreState()


def make_page_callback(existing: Optional[Callable] = None, enabled: bool = True) -> Callable:
    """
    Return an onFirstPage/onLaterPages callback that runs ``existing`` (if any)
    and then draws the watermark when ``enabled`` is True.
    """

    def _callback(canv, doc):
        if existing is not None:
            existing(canv, doc)
        if enabled:
            draw_watermark(canv, doc)

    return _callback
