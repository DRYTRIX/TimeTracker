from datetime import datetime
from app import db


class InvoiceTemplate(db.Model):
    """Reusable invoice templates/themes with customizable HTML and CSS."""

    __tablename__ = "invoice_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    description = db.Column(db.String(255), nullable=True)
    html = db.Column(db.Text, nullable=True)
    css = db.Column(db.Text, nullable=True)
    is_default = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<InvoiceTemplate {self.name}>"
