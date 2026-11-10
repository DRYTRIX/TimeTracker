from datetime import datetime
from decimal import Decimal, InvalidOperation

from app import db


class InvoicePeppolTransmission(db.Model):
    """Track Peppol sends for an invoice (audit + retry support)."""

    __tablename__ = "invoice_peppol_transmissions"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)

    provider = db.Column(db.String(50), nullable=False, default="generic")
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending, sent, failed

    sender_endpoint_id = db.Column(db.String(100), nullable=True)
    sender_scheme_id = db.Column(db.String(20), nullable=True)
    recipient_endpoint_id = db.Column(db.String(100), nullable=True)
    recipient_scheme_id = db.Column(db.String(20), nullable=True)

    document_id = db.Column(db.String(100), nullable=True)  # usually invoice_number
    ubl_sha256 = db.Column(db.String(64), nullable=True)
    ubl_xml = db.Column(db.Text, nullable=True)

    message_id = db.Column(db.String(200), nullable=True)
    response_payload = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)

    invoice = db.relationship("Invoice", backref=db.backref("peppol_transmissions", lazy="dynamic"))

    def mark_sent(self, message_id=None, response_payload=None):
        self.status = "sent"
        self.sent_at = datetime.utcnow()
        if message_id:
            self.message_id = str(message_id)
        if response_payload is not None:
            self.response_payload = response_payload

    def mark_failed(self, error_message, response_payload=None):
        self.status = "failed"
        self.error_message = str(error_message) if error_message is not None else "Unknown error"
        if response_payload is not None:
            self.response_payload = response_payload

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "provider": self.provider,
            "status": self.status,
            "sender_endpoint_id": self.sender_endpoint_id,
            "sender_scheme_id": self.sender_scheme_id,
            "recipient_endpoint_id": self.recipient_endpoint_id,
            "recipient_scheme_id": self.recipient_scheme_id,
            "document_id": self.document_id,
            "ubl_sha256": self.ubl_sha256,
            "message_id": self.message_id,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }


class PeppolInboundDocument(db.Model):
    """Inbound Peppol documents received via the access-point bridge inbox."""

    __tablename__ = "peppol_inbound_documents"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    provider = db.Column(db.String(50), nullable=False, default="letspeppol")
    direction = db.Column(db.String(20), nullable=False, default="inbound")

    partner_peppol_id = db.Column(db.String(120), nullable=True, index=True)
    owner_peppol_id = db.Column(db.String(120), nullable=True)
    document_type = db.Column(db.String(40), nullable=True)  # invoice / credit_note / …
    document_number = db.Column(db.String(100), nullable=True, index=True)
    issue_date = db.Column(db.Date, nullable=True)
    currency = db.Column(db.String(3), nullable=True)
    total_amount = db.Column(db.Numeric(12, 2), nullable=True)

    ubl_xml = db.Column(db.Text, nullable=True)
    ubl_sha256 = db.Column(db.String(64), nullable=True)
    processed_status = db.Column(db.String(100), nullable=True)
    raw_payload = db.Column(db.JSON, nullable=True)

    # new | acknowledged | error
    status = db.Column(db.String(20), nullable=False, default="new", index=True)
    error_message = db.Column(db.Text, nullable=True)
    matched_client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    acknowledged_at = db.Column(db.DateTime, nullable=True)

    matched_client = db.relationship("Client", foreign_keys=[matched_client_id])

    def mark_acknowledged(self):
        self.status = "acknowledged"
        self.acknowledged_at = datetime.utcnow()
        self.error_message = None

    def mark_error(self, message: str):
        self.status = "error"
        self.error_message = str(message) if message is not None else "Unknown error"

    def to_dict(self):
        total = self.total_amount
        if isinstance(total, Decimal):
            total_out = str(total)
        elif total is None:
            total_out = None
        else:
            try:
                total_out = str(Decimal(total))
            except (InvalidOperation, TypeError, ValueError):
                total_out = str(total)
        return {
            "id": self.id,
            "external_id": self.external_id,
            "provider": self.provider,
            "direction": self.direction,
            "partner_peppol_id": self.partner_peppol_id,
            "owner_peppol_id": self.owner_peppol_id,
            "document_type": self.document_type,
            "document_number": self.document_number,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "currency": self.currency,
            "total_amount": total_out,
            "ubl_sha256": self.ubl_sha256,
            "processed_status": self.processed_status,
            "status": self.status,
            "error_message": self.error_message,
            "matched_client_id": self.matched_client_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }
