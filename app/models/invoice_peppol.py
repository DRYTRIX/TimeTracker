from datetime import datetime

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

