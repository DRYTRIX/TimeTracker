"""Client legal entities: who an invoice is billed to.

In TimeTracker a client is both the brand and one legal entity (name, address and VAT on the
client). Some clients pay from several legal entities, or switch entities over time. A client
keeps them here; an invoice picks one as "Bill to".

Part of the optional "Client legal entities" module (``client_entities``). With the module off,
or with no entity on an invoice, invoices use the client's own details as before.
"""

from datetime import datetime

from app import db

STATUSES = ("active", "archived")


class ClientEntity(db.Model):
    """A legal entity of a client that invoices can be billed to."""

    __tablename__ = "client_entities"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    legal_name = db.Column(db.String(255), nullable=False)
    registration_number = db.Column(db.String(100), nullable=True)
    vat_number = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(2), nullable=True)  # ISO 3166-1 alpha-2
    address = db.Column(db.Text, nullable=True)
    email = db.Column(db.String(200), nullable=True)  # where invoices to this entity go
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    client = db.relationship(
        "Client",
        backref=db.backref("legal_entities", lazy="dynamic", cascade="all, delete-orphan", passive_deletes=True),
    )

    def __repr__(self):
        return f"<ClientEntity {self.legal_name}>"

    @property
    def is_active(self):
        return self.status == "active"

    @property
    def label(self):
        return " · ".join(p for p in (self.legal_name, self.country) if p)

    def is_used(self):
        from app.models.invoice import Invoice

        return db.session.query(Invoice.id).filter(Invoice.client_entity_id == self.id).first() is not None

    def buyer_snapshot(self):
        """The "Bill to" details, copied into the invoice."""
        return {
            "client_entity_id": self.id,
            "legal_name": self.legal_name or "",
            "registration_number": self.registration_number or "",
            "vat_number": self.vat_number or "",
            "country": self.country or "",
            "address": self.address or "",
            "email": self.email or "",
        }
