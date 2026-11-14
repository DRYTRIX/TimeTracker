"""FatturaPA / SDI transmission audit model."""

from datetime import datetime

from app import db

# Terminal statuses that no longer need polling
SDI_FINAL_STATUSES = frozenset({"delivered", "not_delivered", "rejected", "accepted", "refused", "expired", "failed"})

# Map SDI notification types to transmission status
SDI_NOTIFICATION_STATUS = {
    "RC": "delivered",  # Ricevuta di consegna
    "NS": "rejected",  # Notifica di scarto
    "MC": "not_delivered",  # Mancata consegna (still legally issued)
    "NE": "accepted",  # Notifica esito (accepted or refused — refined by detail)
    "DT": "expired",  # Decorrenza termini
    "AT": "failed",  # Attestazione di trasmissione con impossibilità di recapito
}


class InvoiceSdiTransmission(db.Model):
    """Track SDI (FatturaPA) sends for an invoice."""

    __tablename__ = "invoice_sdi_transmissions"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)

    filename = db.Column(db.String(100), nullable=True)
    progressivo = db.Column(db.String(10), nullable=True)
    formato = db.Column(db.String(5), nullable=True)  # FPR12 | FPA12
    xml = db.Column(db.Text, nullable=True)
    xml_sha256 = db.Column(db.String(64), nullable=True)

    # pending, sent, delivered, not_delivered, rejected, accepted, refused, expired, failed
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)

    sdi_identifier = db.Column(db.String(100), nullable=True)
    message_id = db.Column(db.String(200), nullable=True)
    notifications = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    invoice = db.relationship("Invoice", backref=db.backref("sdi_transmissions", lazy="dynamic"))

    def mark_sent(self, message_id=None, sdi_identifier=None, response_payload=None):
        self.status = "sent"
        self.sent_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        if message_id:
            self.message_id = str(message_id)
        if sdi_identifier:
            self.sdi_identifier = str(sdi_identifier)
        if response_payload is not None:
            notes = list(self.notifications or [])
            notes.append({"type": "send_response", "payload": response_payload, "date": datetime.utcnow().isoformat()})
            self.notifications = notes

    def mark_failed(self, error_message, response_payload=None):
        self.status = "failed"
        self.updated_at = datetime.utcnow()
        self.error_message = str(error_message) if error_message is not None else "Unknown error"
        if response_payload is not None:
            notes = list(self.notifications or [])
            notes.append({"type": "error", "payload": response_payload, "date": datetime.utcnow().isoformat()})
            self.notifications = notes

    def apply_notification(self, notif_type: str, detail=None, date=None):
        """Apply an SDI notification type (RC/NS/MC/NE/DT/AT) and update status."""
        ntype = (notif_type or "").strip().upper()
        notes = list(self.notifications or [])
        notes.append(
            {
                "type": ntype,
                "detail": detail,
                "date": date or datetime.utcnow().isoformat(),
            }
        )
        self.notifications = notes
        self.updated_at = datetime.utcnow()

        if ntype == "NE":
            # Notifica esito: detail may indicate acceptance or refusal
            detail_s = str(detail or "").lower()
            if any(x in detail_s for x in ("rifiut", "refus", "ec02", "reject")):
                self.status = "refused"
            else:
                self.status = "accepted"
            return

        mapped = SDI_NOTIFICATION_STATUS.get(ntype)
        if mapped:
            self.status = mapped
            if ntype == "NS" and detail:
                self.error_message = str(detail)[:2000]

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "filename": self.filename,
            "progressivo": self.progressivo,
            "formato": self.formato,
            "xml_sha256": self.xml_sha256,
            "status": self.status,
            "sdi_identifier": self.sdi_identifier,
            "message_id": self.message_id,
            "error_message": self.error_message,
            "notifications": self.notifications,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
