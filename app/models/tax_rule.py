from datetime import datetime
from app import db


class TaxRule(db.Model):
    """Flexible tax rules per country/region/client with effective date ranges."""

    __tablename__ = "tax_rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(2), nullable=True)  # ISO-3166-1 alpha-2
    region = db.Column(db.String(50), nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True)
    tax_code = db.Column(db.String(50), nullable=True)  # e.g., VAT, GST
    rate_percent = db.Column(db.Numeric(7, 4), nullable=False, default=0)
    compound = db.Column(db.Boolean, default=False, nullable=False)
    inclusive = db.Column(db.Boolean, default=False, nullable=False)  # If true, prices include tax
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<TaxRule {self.name} {self.rate_percent}%>"
