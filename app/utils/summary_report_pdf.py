"""
Summary report PDF export – one-page PDF with today/week/month hours and top projects.
Uses ReportLab (same as time_entries_pdf).
"""

from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Spacer,
    Paragraph,
)

# Colors (aligned with time_entries_pdf)
BRAND_COLOR = colors.HexColor("#1e3a5f")
HEADER_BG = colors.HexColor("#1e3a5f")
HEADER_FG = colors.HexColor("#ffffff")
ROW_ALT_BG = colors.HexColor("#f0f4f8")
GRID_LIGHT = colors.HexColor("#dde3ea")
MUTED_TEXT = colors.HexColor("#64748b")

MARGIN = 1.5 * cm
PAGE_SIZE = A4


def build_summary_report_pdf(today_hours, week_hours, month_hours, project_stats):
    """
    Build a one-page Summary Report PDF.

    Args:
        today_hours: float
        week_hours: float
        month_hours: float
        project_stats: list of dicts with keys "project" (object with .name) and "hours" (float)

    Returns:
        bytes: PDF file content
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    elements = []

    # Title
    title_style = ParagraphStyle(
        "SummaryTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=BRAND_COLOR,
    )
    elements.append(Paragraph("Summary Report", title_style))
    elements.append(Spacer(1, 6))

    # Stats row: Today | Week | Month
    stats_data = [
        ["Today's Hours", "Week's Hours", "Month's Hours"],
        [f"{today_hours:.2f} h", f"{week_hours:.2f} h", f"{month_hours:.2f} h"],
    ]
    stats_table = Table(
        stats_data,
        colWidths=[5 * cm, 5 * cm, 5 * cm],
        rowHeights=[0.7 * cm, 0.9 * cm],
    )
    stats_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
                ("ALIGN", (0, 0), (-1, -1), TA_CENTER),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, 1), 12),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, GRID_LIGHT),
            ]
        )
    )
    elements.append(stats_table)
    elements.append(Spacer(1, 12))

    # Top projects table
    sub_title_style = ParagraphStyle(
        "SubTitle",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        textColor=BRAND_COLOR,
    )
    elements.append(Paragraph("Top Projects (Last 30 Days)", sub_title_style))
    elements.append(Spacer(1, 6))

    if project_stats:
        table_data = [["Project", "Total Hours"]]
        for stat in project_stats:
            project_name = stat.get("project")
            name = getattr(project_name, "name", str(project_name)) if project_name else ""
            hours = stat.get("hours", 0)
            table_data.append([name, f"{hours:.2f}"])

        col_widths = [12 * cm, 4 * cm]
        projects_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        projects_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
                    ("ALIGN", (0, 0), (0, -1), TA_LEFT),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [ROW_ALT_BG, colors.white]),
                    ("GRID", (0, 0), (-1, -1), 0.5, GRID_LIGHT),
                ]
            )
        )
        elements.append(projects_table)
    else:
        no_data_style = ParagraphStyle(
            "NoData",
            fontName="Helvetica",
            fontSize=10,
            leading=12,
            textColor=MUTED_TEXT,
        )
        elements.append(Paragraph("No project data for the last 30 days.", no_data_style))

    doc.build(elements)
    return buffer.getvalue()
