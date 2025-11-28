from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone
import json


def local_now():
    """Get current time in local timezone as naive datetime (for database storage)"""
    return now_in_app_timezone().replace(tzinfo=None)


class QuoteTemplate(db.Model):
    """Model for reusable quote templates/presets"""

    __tablename__ = "quote_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)

    # Template content (stored as JSON for flexibility)
    template_data = db.Column(db.Text, nullable=True)  # JSON string with quote configuration

    # Common fields that can be preset
    default_tax_rate = db.Column(db.Numeric(5, 2), nullable=True, default=0)
    default_currency_code = db.Column(db.String(3), nullable=True, default="EUR")
    default_payment_terms = db.Column(db.String(100), nullable=True)
    default_terms = db.Column(db.Text, nullable=True)  # Terms and conditions
    default_valid_until_days = db.Column(db.Integer, nullable=True, default=30)  # Days until expiration

    # Approval workflow defaults
    default_requires_approval = db.Column(db.Boolean, default=False, nullable=False)
    default_approval_level = db.Column(db.Integer, nullable=True, default=1)

    # Default items (stored as JSON)
    default_items = db.Column(db.Text, nullable=True)  # JSON array of quote items

    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    is_public = db.Column(db.Boolean, default=False, nullable=False)  # Whether template is available to all users
    usage_count = db.Column(db.Integer, default=0, nullable=False)  # Track how many times template was used

    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)

    # Relationships
    creator = db.relationship("User", foreign_keys=[created_by], backref="created_quote_templates")

    def __init__(self, name, created_by, **kwargs):
        self.name = name.strip()
        self.created_by = created_by
        self.description = kwargs.get("description", "").strip() if kwargs.get("description") else None
        self.default_tax_rate = kwargs.get("default_tax_rate", 0)
        self.default_currency_code = kwargs.get("default_currency_code", "EUR")
        self.default_payment_terms = (
            kwargs.get("default_payment_terms", "").strip() if kwargs.get("default_payment_terms") else None
        )
        self.default_terms = kwargs.get("default_terms", "").strip() if kwargs.get("default_terms") else None
        self.default_valid_until_days = kwargs.get("default_valid_until_days", 30)
        self.default_requires_approval = kwargs.get("default_requires_approval", False)
        self.default_approval_level = kwargs.get("default_approval_level", 1)
        self.is_public = kwargs.get("is_public", False)
        self.default_items = kwargs.get("default_items")  # JSON string
        self.template_data = kwargs.get("template_data")  # JSON string

    def __repr__(self):
        return f"<QuoteTemplate {self.name}>"

    @property
    def items_list(self):
        """Get default items as a list"""
        if not self.default_items:
            return []
        try:
            return json.loads(self.default_items)
        except (json.JSONDecodeError, TypeError):
            return []

    @items_list.setter
    def items_list(self, value):
        """Set default items from a list"""
        if value:
            self.default_items = json.dumps(value)
        else:
            self.default_items = None

    @property
    def data_dict(self):
        """Get template data as a dictionary"""
        if not self.template_data:
            return {}
        try:
            return json.loads(self.template_data)
        except (json.JSONDecodeError, TypeError):
            return {}

    @data_dict.setter
    def data_dict(self, value):
        """Set template data from a dictionary"""
        if value:
            self.template_data = json.dumps(value)
        else:
            self.template_data = None

    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        self.updated_at = local_now()

    def apply_to_quote(self, quote):
        """Apply template settings to a quote object"""
        quote.tax_rate = self.default_tax_rate or quote.tax_rate
        quote.currency_code = self.default_currency_code or quote.currency_code
        quote.payment_terms = self.default_payment_terms or quote.payment_terms
        quote.terms = self.default_terms or quote.terms
        quote.requires_approval = self.default_requires_approval
        quote.approval_level = self.default_approval_level or 1

        # Apply default items
        items = self.items_list
        if items:
            from app.models import QuoteItem
            from decimal import Decimal

            for item_data in items:
                item = QuoteItem(
                    quote_id=quote.id,
                    description=item_data.get("description", ""),
                    quantity=Decimal(str(item_data.get("quantity", 1))),
                    unit_price=Decimal(str(item_data.get("unit_price", 0))),
                    unit=item_data.get("unit"),
                )
                db.session.add(item)

    def to_dict(self):
        """Convert template to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "default_tax_rate": float(self.default_tax_rate) if self.default_tax_rate else 0,
            "default_currency_code": self.default_currency_code,
            "default_payment_terms": self.default_payment_terms,
            "default_terms": self.default_terms,
            "default_valid_until_days": self.default_valid_until_days,
            "default_requires_approval": self.default_requires_approval,
            "default_approval_level": self.default_approval_level,
            "default_items": self.items_list,
            "template_data": self.data_dict,
            "is_public": self.is_public,
            "usage_count": self.usage_count,
            "created_by": self.created_by,
            "creator": self.creator.username if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_user_templates(cls, user_id, include_public=True):
        """Get templates available to a user"""
        query = cls.query.filter(
            db.or_(cls.created_by == user_id, cls.is_public == True if include_public else db.false())
        )
        return query.order_by(cls.usage_count.desc(), cls.name.asc()).all()

    @classmethod
    def get_public_templates(cls):
        """Get all public templates"""
        return cls.query.filter_by(is_public=True).order_by(cls.usage_count.desc(), cls.name.asc()).all()

    @classmethod
    def get_popular_templates(cls, limit=10):
        """Get most used templates"""
        return cls.query.order_by(cls.usage_count.desc()).limit(limit).all()
