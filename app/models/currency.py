from datetime import datetime
from app import db


class Currency(db.Model):
    """Supported currencies and display metadata."""

    __tablename__ = "currencies"

    code = db.Column(db.String(3), primary_key=True)  # e.g., EUR, USD
    name = db.Column(db.String(64), nullable=False)
    symbol = db.Column(db.String(8), nullable=True)  # e.g., €, $
    decimal_places = db.Column(db.Integer, default=2, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Currency {self.code}>"


class ExchangeRate(db.Model):
    """Daily exchange rates between currency pairs."""

    __tablename__ = "exchange_rates"

    id = db.Column(db.Integer, primary_key=True)
    base_code = db.Column(db.String(3), db.ForeignKey("currencies.code"), nullable=False, index=True)
    quote_code = db.Column(db.String(3), db.ForeignKey("currencies.code"), nullable=False, index=True)
    rate = db.Column(db.Numeric(18, 8), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    source = db.Column(db.String(50), nullable=True)  # e.g., ECB, exchangerate.host

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("base_code", "quote_code", "date", name="uq_exchange_rate_day"),)

    def __repr__(self):
        return f"<ExchangeRate {self.base_code}/{self.quote_code} {self.date} {self.rate}>"
