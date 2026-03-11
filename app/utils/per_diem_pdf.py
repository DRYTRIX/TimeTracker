"""
Per diem PDF export – professional report using ReportLab.
Same visual style as time_entries_pdf and mileage_pdf.
"""

from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Spacer,
    Paragraph,
)

BRAND_COLOR = colors.HexColor("#1e3a5f")
HEADER_BG = colors.HexColor("#1e3a5f")
HEADER_FG = colors.HexColor("#ffffff")
ROW_ALT_BG = colors.HexColor("#f0f4f8")
ROW_NORMAL_BG = colors.HexColor("#ffffff")
GRID_LIGHT = colors.HexColor("#dde3ea")
TOTALS_BG = colors.HexColor("#1e3a5f")
TOTALS_FG = colors.HexColor("#ffffff")
MUTED_TEXT = colors.HexColor("#64748b")

FONT_SIZE = 9
HEADER_FONT_SIZE = 10
CELL_PAD_H = 6
CELL_PAD_V = 5
HEADER_PAD_V = 7

PAGE_SIZE = landscape(A4)
MARGIN = 1.0 * cm
BOTTOM_MARGIN = 1.2 * cm
USABLE_WIDTH_CM = 27.7

# 8 columns: Start Date, End Date, User, Trip Purpose, Location, Full/Half Days, Amount, Status
COL_WIDTHS_CM = [2.2, 2.2, 2.4, 5.0, 5.0, 2.4, 2.5, 2.0]
COL_WIDTHS = [w * cm for w in COL_WIDTHS_CM]

NOTES_STYLE = ParagraphStyle(
    "NotesCell",
    fontName="Helvetica",
    fontSize=FONT_SIZE,
    leading=FONT_SIZE + 2,
    alignment=TA_LEFT,
    wordWrap="CJK",
    splitLongWords=True,
)


def _safe_str(val, fallback=""):
    if val is None:
        return fallback
    s = str(val).strip()
    return s if s else fallback


def _make_cell_paragraph(text):
    clean = _safe_str(text)
    if not clean:
        return ""
    clean = clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(clean, NOTES_STYLE)


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED_TEXT)
    page_num = canvas.getPageNumber()
    canvas.drawRightString(doc.pagesize[0] - MARGIN, 0.5 * cm, f"Page {page_num}")
    canvas.restoreState()


def _build_report_header(start_date=None, end_date=None, filters=None):
    elements = []

    title_style = ParagraphStyle(
        "ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=BRAND_COLOR,
    )
    elements.append(Paragraph("Per Diem Report", title_style))
    elements.append(Spacer(1, 4))

    accent = Table([[""]], colWidths=[USABLE_WIDTH_CM * cm], rowHeights=[2])
    accent.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_COLOR),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(accent)
    elements.append(Spacer(1, 8))

    meta_style = ParagraphStyle(
        "ReportMeta",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=MUTED_TEXT,
    )

    if start_date and end_date:
        period = f"Period: {start_date} to {end_date}"
    elif start_date:
        period = f"From: {start_date}"
    elif end_date:
        period = f"Until: {end_date}"
    else:
        period = "Period: All dates"

    try:
        from app.utils.timezone import get_user_datetime_format
        gen_fmt = get_user_datetime_format()
    except Exception:
        gen_fmt = "%Y-%m-%d %H:%M"
    generated = f"Generated: {datetime.now().strftime(gen_fmt)}"

    meta_left = Paragraph(period, meta_style)
    meta_right_style = ParagraphStyle("ReportMetaRight", parent=meta_style, alignment=2)
    meta_right = Paragraph(generated, meta_right_style)
    meta_table = Table(
        [[meta_left, meta_right]],
        colWidths=[USABLE_WIDTH_CM * 0.6 * cm, USABLE_WIDTH_CM * 0.4 * cm],
    )
    meta_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(meta_table)

    if filters:
        filter_parts = [f"{label}: {value}" for label, value in filters.items() if value]
        if filter_parts:
            filter_style = ParagraphStyle(
                "FilterMeta",
                fontName="Helvetica-Oblique",
                fontSize=8,
                leading=11,
                textColor=MUTED_TEXT,
            )
            elements.append(Spacer(1, 2))
            elements.append(Paragraph("Filters: " + " | ".join(filter_parts), filter_style))

    elements.append(Spacer(1, 12))
    return elements


def build_per_diem_pdf(entries, start_date=None, end_date=None, filters=None):
    """
    Build a PDF report of per diem claims.

    Args:
        entries: List of PerDiem objects (with user, project, client loaded).
        start_date: Optional start date string for the report header.
        end_date: Optional end date string for the report header.
        filters: Optional dict of active filter labels.

    Returns:
        bytes: PDF file content.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=BOTTOM_MARGIN,
    )

    story = []
    story.extend(_build_report_header(start_date, end_date, filters))

    headers = ["Start Date", "End Date", "User", "Trip Purpose", "Location", "Full / Half Days", "Amount", "Status"]

    if not entries:
        empty_style = ParagraphStyle(
            "EmptyState",
            fontName="Helvetica-Oblique",
            fontSize=11,
            leading=14,
            textColor=MUTED_TEXT,
        )
        story.append(Spacer(1, 20))
        story.append(Paragraph("No per diem claims found for the selected filters.", empty_style))
    else:
        table_data = [headers]
        total_amount = 0

        for entry in entries:
            amount = float(entry.calculated_amount or 0)
            total_amount += amount

            location = f"{_safe_str(entry.city)}, {_safe_str(entry.country)}" if entry.city else _safe_str(entry.country)
            days_str = f"{entry.full_days or 0} / {entry.half_days or 0}"

            row = [
                entry.start_date.strftime("%Y-%m-%d") if entry.start_date else "",
                entry.end_date.strftime("%Y-%m-%d") if entry.end_date else "",
                _safe_str(entry.user.display_name if entry.user else ""),
                _make_cell_paragraph(entry.trip_purpose or "") or " ",
                _safe_str(location),
                days_str,
                f"{amount:.2f}",
                _safe_str(entry.status),
            ]
            table_data.append(row)

        table_data.append(["", "", "", "Total", "", "", f"{total_amount:.2f}", ""])
        total_row_idx = len(table_data) - 1

        style = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), HEADER_FONT_SIZE),
            ("BOTTOMPADDING", (0, 0), (-1, 0), HEADER_PAD_V),
            ("TOPPADDING", (0, 0), (-1, 0), HEADER_PAD_V),
            ("LEFTPADDING", (0, 0), (-1, -1), CELL_PAD_H),
            ("RIGHTPADDING", (0, 0), (-1, -1), CELL_PAD_H),
            ("TOPPADDING", (0, 0), (-1, -1), CELL_PAD_V),
            ("BOTTOMPADDING", (0, 0), (-1, -1), CELL_PAD_V),
            ("GRID", (0, 0), (-1, -1), 0.5, GRID_LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, total_row_idx), (-1, total_row_idx), TOTALS_BG),
            ("TEXTCOLOR", (0, total_row_idx), (-1, total_row_idx), TOTALS_FG),
            ("FONTNAME", (0, total_row_idx), (-1, total_row_idx), "Helvetica-Bold"),
        ]

        nrows = len(table_data)
        for r in range(1, nrows - 1):
            bg = ROW_ALT_BG if r % 2 == 1 else ROW_NORMAL_BG
            style.append(("BACKGROUND", (0, r), (-1, r), bg))

        table = Table(table_data, colWidths=COL_WIDTHS, repeatRows=1)
        table.setStyle(TableStyle(style))
        story.append(table)

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()
