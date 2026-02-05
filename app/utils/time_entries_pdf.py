"""
Time entries PDF export – data-only table using ReportLab.
Produces a clean PDF with a single table of time entry data (no headers/footers/nav).
"""

from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer


# Table styling – compact, readable look
HEADER_BG = colors.HexColor("#1e3a5f")
HEADER_FG = colors.HexColor("#ffffff")
ROW_ALT_BG = colors.HexColor("#f8fafc")
GRID_LIGHT = colors.HexColor("#e2e8f0")
GRID_HEADER = colors.HexColor("#334155")
FONT_SIZE = 8
HEADER_FONT_SIZE = 9
CELL_PAD_H = 6
CELL_PAD_V = 4
HEADER_PAD_V = 6


def _fmt_dt(dt):
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M")
    return str(dt)


def _fmt_date(dt):
    if dt is None:
        return ""
    if hasattr(dt, "date"):
        return dt.date().isoformat()
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d")
    return str(dt)


def _str(val, max_len=80):
    if val is None:
        return ""
    s = str(val).strip()
    if max_len and len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


def _cell_text(val):
    """Normalize cell text: single line, no control chars. Use plain strings so table split has no bug."""
    s = _str(val)
    if not s:
        return " "
    return " ".join(s.split())


def build_time_entries_pdf(entries):
    """
    Build a PDF containing only a table of time entry data.

    Args:
        entries: List of TimeEntry objects (with user, project, client, task loaded).

    Returns:
        bytes: PDF file content.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=0.75 * cm,
        rightMargin=0.75 * cm,
        topMargin=0.75 * cm,
        bottomMargin=0.75 * cm,
    )
    # Header row (column titles)
    headers = [
        "Date",
        "User",
        "Project",
        "Task",
        "Start",
        "End",
        "Duration",
        "Notes",
        "Tags",
        "Billable",
        "Source",
    ]
    data = [headers]

    for entry in entries:
        duration_seconds = getattr(entry, "duration_seconds", None)
        duration_hours = (duration_seconds or 0) / 3600
        duration_str = f"{duration_hours:.2f}h"

        row = [
            _fmt_date(entry.start_time),
            _str(entry.user.username if entry.user else ""),
            _str(entry.project.name if entry.project else (entry.client.name if entry.client else "")),
            _str(entry.task.name if entry.task else ""),
            _fmt_dt(entry.start_time),
            _fmt_dt(entry.end_time),
            duration_str,
            _str(entry.notes or "", max_len=60),
            _str(entry.tags or "", max_len=40),
            "Yes" if entry.billable else "No",
            _str(getattr(entry, "source", "") or "manual"),
        ]
        data.append(row)

    if len(data) == 1:
        data.append(["(No time entries)", "", "", "", "", "", "", "", "", "", ""])

    # Column widths – fill A4 landscape usable width (29.7 - 1.5 margin = 28.2 cm)
    col_widths_cm = [
        2.4,   # Date
        2.2,   # User
        3.6,   # Project
        2.8,   # Task
        2.6,   # Start
        2.6,   # End
        1.3,   # Duration
        5.7,   # Notes
        2.4,   # Tags
        0.7,   # Billable
        0.9,   # Source
    ]
    col_widths = [w * cm for w in col_widths_cm]

    # All cells as plain strings (no Paragraphs) to avoid ReportLab table-split height bug (2147483663).
    # Paginate: one table per page so no table ever splits; header on every page.
    ROWS_PER_PAGE = 40
    header_row = list(data[0])
    body_rows = data[1:]
    story = []

    for start in range(0, len(body_rows), ROWS_PER_PAGE):
        chunk_rows = body_rows[start : start + ROWS_PER_PAGE]
        table_data = [header_row] + [[_cell_text(c) for c in row] for row in chunk_rows]
        nrows = len(table_data)
        t = Table(table_data, colWidths=col_widths, repeatRows=0)
        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), HEADER_FONT_SIZE),
            ("TOPPADDING", (0, 0), (-1, 0), HEADER_PAD_V),
            ("BOTTOMPADDING", (0, 0), (-1, 0), HEADER_PAD_V),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, GRID_HEADER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (4, 0), (6, -1), "LEFT"),
            ("ALIGN", (7, 0), (-1, -1), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), CELL_PAD_H),
            ("RIGHTPADDING", (0, 0), (-1, -1), CELL_PAD_H),
            ("TOPPADDING", (0, 0), (-1, -1), CELL_PAD_V),
            ("BOTTOMPADDING", (0, 0), (-1, -1), CELL_PAD_V),
            ("FONTSIZE", (0, 1), (-1, -1), FONT_SIZE),
            ("GRID", (0, 0), (-1, -1), 0.5, GRID_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.75, GRID_HEADER),
        ]
        for r in range(1, nrows):
            if r % 2 == 0:
                style_commands.append(("BACKGROUND", (0, r), (-1, r), ROW_ALT_BG))
        t.setStyle(TableStyle(style_commands))
        story.append(t)
        if start + ROWS_PER_PAGE < len(body_rows):
            story.append(Spacer(1, 0.5 * cm))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
