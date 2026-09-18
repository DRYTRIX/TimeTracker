"""Purchase Order PDF generation using ReportLab."""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import Settings

BRAND_COLOR = colors.HexColor("#1e3a5f")
HEADER_BG = colors.HexColor("#1e3a5f")
HEADER_FG = colors.HexColor("#ffffff")
ROW_ALT_BG = colors.HexColor("#f0f4f8")
GRID_LIGHT = colors.HexColor("#dde3ea")
MUTED_TEXT = colors.HexColor("#64748b")


class PurchaseOrderPDFGenerator:
    """Generate a printable purchase order PDF."""

    def __init__(self, purchase_order, settings=None):
        self.purchase_order = purchase_order
        self.settings = settings or Settings.get_settings()
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        self.styles.add(
            ParagraphStyle(
                name="POTitle",
                parent=self.styles["Heading1"],
                fontSize=20,
                textColor=BRAND_COLOR,
                spaceAfter=6,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="POSection",
                parent=self.styles["Heading2"],
                fontSize=12,
                textColor=BRAND_COLOR,
                spaceBefore=12,
                spaceAfter=6,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="POBody",
                parent=self.styles["Normal"],
                fontSize=10,
                spaceAfter=4,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="POMuted",
                parent=self.styles["Normal"],
                fontSize=9,
                textColor=MUTED_TEXT,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="PORight",
                parent=self.styles["Normal"],
                fontSize=10,
                alignment=TA_RIGHT,
            )
        )

    def generate_pdf(self):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )
        doc.build(self._build_story(), onFirstPage=self._footer, onLaterPages=self._footer)
        return buffer.getvalue()

    def _footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED_TEXT)
        canvas.drawRightString(doc.pagesize[0] - 1.5 * cm, 0.8 * cm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    def _escape(self, value):
        text = "" if value is None else str(value)
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _build_story(self):
        po = self.purchase_order
        settings = self.settings
        story = []

        company = getattr(settings, "company_name", None) or "TimeTracker"
        story.append(Paragraph(self._escape(company), self.styles["POTitle"]))
        story.append(Paragraph(f"Purchase Order {self._escape(po.po_number)}", self.styles["POSection"]))
        story.append(Spacer(1, 0.3 * cm))

        supplier = po.supplier
        supplier_lines = [supplier.name] if supplier else ["—"]
        if supplier:
            for attr in ("contact_name", "email", "phone", "address", "city", "country"):
                val = getattr(supplier, attr, None)
                if val:
                    supplier_lines.append(str(val))

        company_lines = [company]
        for attr in ("company_address", "company_city", "company_country", "company_email", "company_phone"):
            val = getattr(settings, attr, None)
            if val:
                company_lines.append(str(val))

        meta = [
            ["Order date", po.order_date.isoformat() if po.order_date else "—"],
            ["Expected delivery", po.expected_delivery_date.isoformat() if po.expected_delivery_date else "—"],
            ["Status", (po.status or "").title()],
            ["Currency", po.currency_code or "EUR"],
        ]

        header_data = [
            [
                Paragraph("<br/>".join(self._escape(l) for l in company_lines), self.styles["POBody"]),
                Paragraph("<br/>".join(self._escape(l) for l in supplier_lines), self.styles["POBody"]),
                Paragraph(
                    "<br/>".join(f"<b>{self._escape(k)}:</b> {self._escape(v)}" for k, v in meta),
                    self.styles["POBody"],
                ),
            ]
        ]
        header_table = Table(header_data, colWidths=[6 * cm, 6 * cm, 5.5 * cm])
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(header_table)
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Line items", self.styles["POSection"]))

        rows = [["#", "Description", "Qty", "Unit cost", "Line total"]]
        items = list(po.items) if not hasattr(po.items, "all") else po.items.all()
        for idx, item in enumerate(items, start=1):
            qty = float(item.quantity_ordered or 0)
            unit = float(item.unit_cost or 0)
            line_total = float(getattr(item, "line_total", None) or (qty * unit))
            rows.append(
                [
                    str(idx),
                    Paragraph(self._escape(item.description or ""), self.styles["POBody"]),
                    f"{qty:.2f}",
                    f"{unit:.2f}",
                    f"{line_total:.2f}",
                ]
            )

        items_table = Table(rows, colWidths=[1.2 * cm, 9.5 * cm, 2 * cm, 2.5 * cm, 2.5 * cm])
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, GRID_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
        for i in range(1, len(rows)):
            if i % 2 == 0:
                style_cmds.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT_BG))
        items_table.setStyle(TableStyle(style_cmds))
        story.append(items_table)
        story.append(Spacer(1, 0.4 * cm))

        totals = [
            ["Subtotal", f"{float(po.subtotal or 0):.2f} {po.currency_code or ''}"],
            ["Tax", f"{float(po.tax_amount or 0):.2f} {po.currency_code or ''}"],
            ["Shipping", f"{float(po.shipping_cost or 0):.2f} {po.currency_code or ''}"],
            ["Total", f"{float(po.total_amount or 0):.2f} {po.currency_code or ''}"],
        ]
        totals_table = Table(totals, colWidths=[4 * cm, 4 * cm], hAlign="RIGHT")
        totals_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("TEXTCOLOR", (0, -1), (-1, -1), BRAND_COLOR),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(totals_table)

        if po.notes:
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph("Notes", self.styles["POSection"]))
            story.append(Paragraph(self._escape(po.notes), self.styles["POBody"]))

        return story
