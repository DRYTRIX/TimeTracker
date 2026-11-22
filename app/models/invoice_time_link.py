"""Link between a time entry and the invoice (and line) that bills it.

A time entry is billed when it has an active link: one whose ``released_at`` is empty.
Links are created and removed only by ``app.services.invoice_time_service``.
"""

from datetime import datetime

from app import db

# An entry has at most one active link with a line (on any invoice) and at most one active link
# without a line (prepaid hours), so the same hours are never billed twice.
ACTIVE_LINE_CONDITION = "released_at IS NULL AND invoice_item_id IS NOT NULL"
ACTIVE_PREPAID_CONDITION = "released_at IS NULL AND invoice_item_id IS NULL"


class InvoiceTimeLink(db.Model):
    """One time entry on one invoice line.

    ``invoice_item_id`` is empty only for an entry fully covered by prepaid hours: such an entry has
    no line. ``hours`` is the part of the entry billed by this invoice; it is less than the entry's
    hours when prepaid hours cover the rest. An entry has at most one active link with a line and at
    most one without; the service keeps both on the same invoice.

    Cancelling an invoice releases its links (``released_at``) instead of deleting them, so the
    history stays. Deleting a line, a draft invoice or an entry deletes its links.
    """

    __tablename__ = "invoice_time_links"

    id = db.Column(db.Integer, primary_key=True)
    time_entry_id = db.Column(
        db.Integer, db.ForeignKey("time_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_item_id = db.Column(
        db.Integer, db.ForeignKey("invoice_items.id", ondelete="CASCADE"), nullable=True, index=True
    )
    hours = db.Column(db.Numeric(10, 4), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    released_at = db.Column(db.DateTime, nullable=True, index=True)
    released_reason = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.Index(
            "uq_invoice_time_links_active_line",
            "time_entry_id",
            unique=True,
            postgresql_where=db.text(ACTIVE_LINE_CONDITION),
            sqlite_where=db.text(ACTIVE_LINE_CONDITION),
        ),
        db.Index(
            "uq_invoice_time_links_active_prepaid",
            "time_entry_id",
            unique=True,
            postgresql_where=db.text(ACTIVE_PREPAID_CONDITION),
            sqlite_where=db.text(ACTIVE_PREPAID_CONDITION),
        ),
    )

    time_entry = db.relationship(
        "TimeEntry",
        backref=db.backref("invoice_links", lazy="dynamic", cascade="all, delete-orphan"),
    )
    invoice = db.relationship(
        "Invoice",
        backref=db.backref("time_links", lazy="dynamic", cascade="all, delete-orphan"),
    )
    invoice_item = db.relationship(
        "InvoiceItem",
        backref=db.backref("time_links", lazy="dynamic", cascade="all, delete-orphan"),
    )

    @property
    def is_active(self) -> bool:
        return self.released_at is None

    def __repr__(self):
        state = "active" if self.is_active else "released"
        return (
            f"<InvoiceTimeLink entry={self.time_entry_id} invoice={self.invoice_id} "
            f"item={self.invoice_item_id} {state}>"
        )
