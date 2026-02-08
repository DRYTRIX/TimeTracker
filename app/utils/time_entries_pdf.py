"""
Time entries PDF export – professional report using ReportLab.
Produces a clean, readable PDF with a report header, date-grouped table,
summary totals, and page numbers.
"""

from io import BytesIO
from datetime import datetime
from collections import OrderedDict

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
    KeepTogether,
)


# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
BRAND_COLOR = colors.HexColor("#1e3a5f")
HEADER_BG = colors.HexColor("#1e3a5f")
HEADER_FG = colors.HexColor("#ffffff")
ROW_ALT_BG = colors.HexColor("#f0f4f8")
ROW_NORMAL_BG = colors.HexColor("#ffffff")
GRID_LIGHT = colors.HexColor("#dde3ea")
GRID_HEADER = colors.HexColor("#334155")
DATE_GROUP_BG = colors.HexColor("#e8edf3")
DATE_GROUP_FG = colors.HexColor("#1e3a5f")
TOTALS_BG = colors.HexColor("#1e3a5f")
TOTALS_FG = colors.HexColor("#ffffff")
MUTED_TEXT = colors.HexColor("#64748b")

# ---------------------------------------------------------------------------
# Font / spacing constants
# ---------------------------------------------------------------------------
FONT_SIZE = 9
HEADER_FONT_SIZE = 10
DATE_GROUP_FONT_SIZE = 9
CELL_PAD_H = 6
CELL_PAD_V = 5
HEADER_PAD_V = 7

# Page layout
PAGE_SIZE = landscape(A4)
MARGIN = 1.0 * cm
BOTTOM_MARGIN = 1.2 * cm  # extra room for page number

# Usable width: 29.7cm - 2*1.0cm margin = 27.7cm
USABLE_WIDTH_CM = 27.7

# Column widths (8 columns)  –  must sum to ~USABLE_WIDTH_CM
COL_WIDTHS_CM = [
    2.6,   # User
    3.0,   # Client
    3.4,   # Project
    2.8,   # Task
    3.2,   # Time (start – end)
    1.6,   # Duration
    9.5,   # Notes
    1.6,   # Billable
]
COL_WIDTHS = [w * cm for w in COL_WIDTHS_CM]
NUM_COLS = len(COL_WIDTHS)

# Paragraph style for wrapping notes
NOTES_STYLE = ParagraphStyle(
    "NotesCell",
    fontName="Helvetica",
    fontSize=FONT_SIZE,
    leading=FONT_SIZE + 2,
    alignment=TA_LEFT,
    wordWrap="CJK",
    splitLongWords=True,
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _fmt_time(dt):
    """Format datetime using the current user's time format preference."""
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        try:
            from app.utils.timezone import get_user_time_format
            return dt.strftime(get_user_time_format())
        except Exception:
            return dt.strftime("%H:%M")
    return str(dt)


def _fmt_date_group(dt):
    """Format a date for the group header row, e.g. 'Monday, 06.02.2026'."""
    if dt is None:
        return "Unknown date"
    try:
        from app.utils.timezone import get_user_date_format
        date_fmt = get_user_date_format()
        return dt.strftime(f"%A, {date_fmt}")
    except Exception:
        return str(dt)


def _duration_hhmm(seconds):
    """Convert seconds to HH:MM string."""
    if not seconds or seconds < 0:
        return "00:00"
    total_minutes = int(seconds) // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def _safe_str(val, fallback=""):
    """Safely convert a value to a stripped string."""
    if val is None:
        return fallback
    s = str(val).strip()
    return s if s else fallback


def _make_cell_paragraph(text):
    """Wrap text in a Paragraph for word-wrapping inside table cells (notes, task, client, project)."""
    clean = _safe_str(text)
    if not clean:
        return ""
    # Escape XML-special characters for ReportLab Paragraph
    clean = clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(clean, NOTES_STYLE)


def _make_notes_paragraph(text):
    """Wrap notes text in a Paragraph for word-wrapping inside the table cell."""
    return _make_cell_paragraph(text)


# ---------------------------------------------------------------------------
# Page callback for page numbers
# ---------------------------------------------------------------------------

def _page_footer(canvas, doc):
    """Draw page number at bottom-right of every page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED_TEXT)
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.drawRightString(
        doc.pagesize[0] - MARGIN,
        0.5 * cm,
        text,
    )
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Report header builder
# ---------------------------------------------------------------------------

def _build_report_header(start_date=None, end_date=None, filters=None):
    """Build the story elements for the report header section."""
    elements = []

    # Title
    title_style = ParagraphStyle(
        "ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=BRAND_COLOR,
    )
    elements.append(Paragraph("Time Entries Report", title_style))
    elements.append(Spacer(1, 4))

    # Accent line (drawn via a thin colored table)
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

    # Meta info line(s)
    meta_style = ParagraphStyle(
        "ReportMeta",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=MUTED_TEXT,
    )

    # Period
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

    # Build a two-column layout: period on left, generated on right
    meta_left = Paragraph(period, meta_style)
    meta_right_style = ParagraphStyle(
        "ReportMetaRight",
        parent=meta_style,
        alignment=2,  # TA_RIGHT
    )
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

    # Filter summary
    if filters:
        filter_parts = []
        for label, value in filters.items():
            if value:
                filter_parts.append(f"{label}: {value}")
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


# ---------------------------------------------------------------------------
# Main PDF builder
# ---------------------------------------------------------------------------

def build_time_entries_pdf(entries, start_date=None, end_date=None, filters=None):
    """
    Build a professional PDF report of time entry data.

    Args:
        entries: List of TimeEntry objects (with user, project, client, task loaded).
        start_date: Optional start date string for the report header.
        end_date: Optional end date string for the report header.
        filters: Optional dict of active filter labels, e.g. {"User": "john", "Project": "WebApp"}.

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

    # ── Report header ──────────────────────────────────────────────────
    story.extend(_build_report_header(start_date, end_date, filters))

    # ── Group entries by date ──────────────────────────────────────────
    grouped = _group_entries_by_date(entries)

    total_seconds = 0
    billable_seconds = 0
    entry_count = 0

    if not entries:
        # Empty state
        empty_style = ParagraphStyle(
            "EmptyState",
            fontName="Helvetica-Oblique",
            fontSize=11,
            leading=14,
            textColor=MUTED_TEXT,
        )
        story.append(Spacer(1, 20))
        story.append(Paragraph("No time entries found for the selected filters.", empty_style))
    else:
        # ── Build tables per date group ────────────────────────────────
        headers = ["User", "Client", "Project", "Task", "Time", "Duration", "Notes", "Billable"]

        for date_key, date_entries in grouped.items():
            group_elements = []

            # Date group sub-header
            date_label = _fmt_date_group(date_key)
            date_style = ParagraphStyle(
                "DateGroup",
                fontName="Helvetica-Bold",
                fontSize=DATE_GROUP_FONT_SIZE,
                leading=DATE_GROUP_FONT_SIZE + 3,
                textColor=DATE_GROUP_FG,
            )
            group_elements.append(Spacer(1, 6))
            group_elements.append(Paragraph(date_label, date_style))
            group_elements.append(Spacer(1, 3))

            # Build table data for this date group
            table_data = [headers]
            data_row_indices = []  # track which rows are data (not header)

            for entry in date_entries:
                dur_sec = getattr(entry, "duration_seconds", None) or 0
                total_seconds += dur_sec
                if entry.billable:
                    billable_seconds += dur_sec
                entry_count += 1

                time_range = _fmt_time(entry.start_time)
                if entry.end_time:
                    time_range += f" - {_fmt_time(entry.end_time)}"

                # Use wrapping Paragraphs for long-text columns so they break across lines (like notes)
                client_cell = _make_cell_paragraph(entry.client.name if entry.client else "")
                project_cell = _make_cell_paragraph(entry.project.name if entry.project else "")
                task_cell = _make_cell_paragraph(entry.task.name if entry.task else "")
                notes_cell = _make_notes_paragraph(entry.notes)

                row = [
                    _safe_str(entry.user.username if entry.user else ""),
                    client_cell if client_cell else " ",
                    project_cell if project_cell else " ",
                    task_cell if task_cell else " ",
                    time_range if time_range else " ",
                    _duration_hhmm(dur_sec),
                    notes_cell if notes_cell else " ",
                    "\u2713" if entry.billable else "\u2014",  # checkmark or em-dash
                ]
                data_row_indices.append(len(table_data))
                table_data.append(row)

            nrows = len(table_data)
            t = Table(table_data, colWidths=COL_WIDTHS, repeatRows=1)

            style_commands = [
                # Header row styling
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), HEADER_FONT_SIZE),
                ("TOPPADDING", (0, 0), (-1, 0), HEADER_PAD_V),
                ("BOTTOMPADDING", (0, 0), (-1, 0), HEADER_PAD_V),
                ("LINEBELOW", (0, 0), (-1, 0), 1.5, GRID_HEADER),

                # Global cell styles
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("ALIGN", (5, 1), (5, -1), "CENTER"),  # Duration centered
                ("ALIGN", (7, 0), (7, -1), "CENTER"),   # Billable centered
                ("LEFTPADDING", (0, 0), (-1, -1), CELL_PAD_H),
                ("RIGHTPADDING", (0, 0), (-1, -1), CELL_PAD_H),
                ("TOPPADDING", (0, 1), (-1, -1), CELL_PAD_V),
                ("BOTTOMPADDING", (0, 1), (-1, -1), CELL_PAD_V),

                # Body font size
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), FONT_SIZE),

                # Grid
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, GRID_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.75, GRID_HEADER),
            ]

            # Alternating row backgrounds
            for idx, row_num in enumerate(data_row_indices):
                bg = ROW_ALT_BG if idx % 2 == 1 else ROW_NORMAL_BG
                style_commands.append(("BACKGROUND", (0, row_num), (-1, row_num), bg))

            t.setStyle(TableStyle(style_commands))
            group_elements.append(t)

            # Try to keep the date header with at least the first few rows
            story.append(KeepTogether(group_elements[:5]))
            if len(group_elements) > 5:
                for el in group_elements[5:]:
                    story.append(el)

    # ── Summary totals ─────────────────────────────────────────────────
    if entry_count > 0:
        story.append(Spacer(1, 14))
        story.extend(_build_summary_totals(entry_count, total_seconds, billable_seconds))

    # ── Build PDF ──────────────────────────────────────────────────────
    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    buffer.seek(0)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Helpers for grouping and summary
# ---------------------------------------------------------------------------

def _group_entries_by_date(entries):
    """Group entries by their start date, preserving order."""
    grouped = OrderedDict()
    for entry in entries:
        if entry.start_time:
            date_key = entry.start_time.date() if hasattr(entry.start_time, "date") else entry.start_time
        else:
            date_key = None
        if date_key not in grouped:
            grouped[date_key] = []
        grouped[date_key].append(entry)
    return grouped


def _build_summary_totals(entry_count, total_seconds, billable_seconds):
    """Build the summary totals section at the bottom of the report."""
    elements = []

    total_dur = _duration_hhmm(total_seconds)
    billable_dur = _duration_hhmm(billable_seconds)

    summary_style = ParagraphStyle(
        "SummaryLabel",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=TOTALS_FG,
    )

    # Build a single-row summary table spanning full width
    summary_data = [[
        Paragraph(f"Total: {entry_count} entries", summary_style),
        Paragraph(f"Total Duration: {total_dur}", summary_style),
        Paragraph(f"Billable: {billable_dur}", summary_style),
    ]]

    third = USABLE_WIDTH_CM / 3.0
    summary_table = Table(
        summary_data,
        colWidths=[third * cm, third * cm, third * cm],
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TOTALS_BG),
        ("TEXTCOLOR", (0, 0), (-1, -1), TOTALS_FG),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(summary_table)
    return elements
