"""Time-off request PDF form — printable leave/vacation request with approval block."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BRAND_COLOR = colors.HexColor("#1e3a5f")
MUTED_TEXT = colors.HexColor("#64748b")
GRID_LIGHT = colors.HexColor("#dde3ea")
ROW_ALT_BG = colors.HexColor("#f8fafc")

PAGE_SIZE = A4
MARGIN = 2.0 * cm


def _safe(val, fallback="—"):
    if val is None:
        return fallback
    s = str(val).strip()
    return s if s else fallback


def _para(text: str, style: ParagraphStyle) -> Paragraph:
    clean = _safe(text, "")
    clean = clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(clean or "—", style)


def build_time_off_pdf(request, settings=None) -> bytes:
    """Build a printable time-off request form PDF."""
    from app.models import Settings

    settings = settings or Settings.get_settings()
    user = request.user
    leave_type = request.leave_type
    reviewer = request.reviewer

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    title_style = ParagraphStyle(
        "Title",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=BRAND_COLOR,
        alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "Section",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=BRAND_COLOR,
        spaceBefore=12,
        spaceAfter=6,
    )
    label_style = ParagraphStyle(
        "Label",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=MUTED_TEXT,
    )
    value_style = ParagraphStyle(
        "Value",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.black,
    )
    sig_style = ParagraphStyle(
        "Sig",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.black,
        spaceBefore=24,
    )

    elements = []
    company = _safe(getattr(settings, "company_name", None), "Company")
    elements.append(_para(company, title_style))
    elements.append(Spacer(1, 6))
    elements.append(_para("Time-Off Request Form", title_style))
    elements.append(Spacer(1, 16))

    status = request.status.value if hasattr(request.status, "value") else str(request.status)
    employee_name = _safe(getattr(user, "full_name", None) or getattr(user, "username", None))
    employee_email = _safe(getattr(user, "email", None))

    rows = [
        [_para("Employee", label_style), _para(employee_name, value_style)],
        [_para("Email", label_style), _para(employee_email, value_style)],
        [_para("Leave type", label_style), _para(leave_type.name if leave_type else "—", value_style)],
        [_para("From", label_style), _para(request.start_date.isoformat() if request.start_date else "—", value_style)],
        [_para("To", label_style), _para(request.end_date.isoformat() if request.end_date else "—", value_style)],
        [
            _para("Requested hours", label_style),
            _para(
                f"{float(request.requested_hours):.2f}" if request.requested_hours is not None else "—",
                value_style,
            ),
        ],
        [_para("Status", label_style), _para(status.title(), value_style)],
        [
            _para("Submitted", label_style),
            _para(
                request.submitted_at.strftime("%Y-%m-%d %H:%M") if request.submitted_at else "—",
                value_style,
            ),
        ],
        [_para("Employee comment", label_style), _para(request.requested_comment, value_style)],
    ]

    table = Table(rows, colWidths=[4.5 * cm, 12 * cm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, ROW_ALT_BG]),
                ("BOX", (0, 0), (-1, -1), 0.5, GRID_LIGHT),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, GRID_LIGHT),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table)

    elements.append(_para("Approval", section_style))
    if request.reviewed_at and reviewer:
        reviewer_name = _safe(getattr(reviewer, "full_name", None) or getattr(reviewer, "username", None))
        reviewed_at = request.reviewed_at.strftime("%Y-%m-%d %H:%M")
        elements.append(_para(f"Approved by {reviewer_name} on {reviewed_at}", value_style))
        if request.review_comment:
            elements.append(_para(f"Comment: {request.review_comment}", value_style))
    else:
        elements.append(_para("Pending approval", value_style))

    elements.append(Spacer(1, 20))
    elements.append(_para("Signatures", section_style))

    sig_rows = [
        [
            _para("Employee signature", sig_style),
            _para("Team lead / approver signature", sig_style),
        ],
        [
            _para(f"Name: {employee_name}", value_style),
            _para(
                (
                    f"Name: {_safe(getattr(reviewer, 'full_name', None) or getattr(reviewer, 'username', None), '')}"
                    if reviewer
                    else "Name: ___________________________"
                ),
                value_style,
            ),
        ],
        [
            _para("Date: ___________________________", value_style),
            _para(
                (
                    f"Date: {request.reviewed_at.strftime('%Y-%m-%d')}"
                    if request.reviewed_at
                    else "Date: ___________________________"
                ),
                value_style,
            ),
        ],
        [
            _para("Signature: _______________________", value_style),
            _para("Signature: _______________________", value_style),
        ],
    ]
    sig_table = Table(sig_rows, colWidths=[8.25 * cm, 8.25 * cm])
    sig_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(sig_table)

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    elements.append(Spacer(1, 24))
    elements.append(
        _para(
            f"Generated by TimeTracker on {generated}",
            ParagraphStyle("Footer", fontName="Helvetica", fontSize=8, textColor=MUTED_TEXT, alignment=TA_LEFT),
        )
    )

    doc.build(elements)
    return buffer.getvalue()
