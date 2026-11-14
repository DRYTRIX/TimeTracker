"""Simple ReportLab PDF generator for credit notes."""

from __future__ import annotations

import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_credit_note_pdf(cn) -> bytes:
    """Return PDF bytes for a credit note."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CNTitle", parent=styles["Heading1"], fontSize=18, spaceAfter=12)
    normal = styles["Normal"]

    story = []
    story.append(Paragraph("Credit Note", title_style))
    story.append(Paragraph(f"<b>Number:</b> {cn.credit_number}", normal))
    if cn.issue_date:
        story.append(Paragraph(f"<b>Issue date:</b> {cn.issue_date.isoformat()}", normal))
    story.append(Paragraph(f"<b>Status:</b> {cn.status}", normal))
    if cn.invoice:
        story.append(Paragraph(f"<b>Original invoice:</b> {cn.invoice.invoice_number}", normal))
        story.append(Paragraph(f"<b>Client:</b> {cn.invoice.client_name or ''}", normal))
    if cn.reason:
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Reason:</b> {cn.reason}", normal))
    story.append(Spacer(1, 12))

    items = cn.items.all() if hasattr(cn.items, "all") else list(cn.items or [])
    items = sorted(items, key=lambda x: getattr(x, "position", 0) or 0)
    currency = cn.currency_code or (cn.invoice.currency_code if cn.invoice else "EUR") or "EUR"

    if items:
        data = [["Description", "Qty", "Unit price", "Total"]]
        for item in items:
            data.append(
                [
                    str(item.description or "")[:80],
                    f"{Decimal(str(item.quantity or 0)):.2f}",
                    f"{Decimal(str(item.unit_price or 0)):.2f}",
                    f"{Decimal(str(item.total_amount or 0)):.2f}",
                ]
            )
        table = Table(data, colWidths=[90 * mm, 25 * mm, 30 * mm, 30 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 12))

    subtotal = Decimal(str(cn.subtotal if cn.subtotal is not None else 0))
    tax = Decimal(str(cn.tax_amount if cn.tax_amount is not None else 0))
    total = Decimal(str(cn.total_amount if cn.total_amount is not None else cn.amount or 0))
    story.append(Paragraph(f"<b>Subtotal:</b> {subtotal:.2f} {currency}", normal))
    story.append(Paragraph(f"<b>Tax:</b> {tax:.2f} {currency}", normal))
    story.append(Paragraph(f"<b>Total credit:</b> {total:.2f} {currency}", normal))

    doc.build(story)
    return buffer.getvalue()
