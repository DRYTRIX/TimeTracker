from datetime import datetime
from decimal import Decimal
from app import db


class ExtraGood(db.Model):
    """Extra Good model for tracking additional products/goods on projects and invoices"""
    
    __tablename__ = 'extra_goods'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to either project or invoice (can be both)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=True, index=True)
    
    # Good details
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)  # 'product', 'service', 'material', 'license', 'other'
    
    # Pricing
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False, default='EUR')
    
    # Billing and tracking
    billable = db.Column(db.Boolean, default=True, nullable=False)
    sku = db.Column(db.String(100), nullable=True)  # Stock Keeping Unit / Product Code
    
    # Inventory integration
    stock_item_id = db.Column(db.Integer, db.ForeignKey('stock_items.id'), nullable=True, index=True)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Relationships
    stock_item = db.relationship('StockItem', foreign_keys=[stock_item_id], lazy='joined')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    # project and invoice relationships defined via backref
    creator = db.relationship('User', backref='extra_goods', foreign_keys=[created_by])
    
    def __init__(self, name, unit_price, quantity=1, created_by=None, project_id=None, 
                 invoice_id=None, description=None, category='product', billable=True, 
                 sku=None, currency_code='EUR', stock_item_id=None):
        """Initialize an ExtraGood instance.
        
        Args:
            name: Name of the good/product
            unit_price: Price per unit
            quantity: Quantity (default: 1)
            created_by: ID of the user who created this
            project_id: Optional project ID to associate with
            invoice_id: Optional invoice ID to associate with
            description: Optional detailed description
            category: Category of the good (product, service, material, license, other)
            billable: Whether this good is billable
            sku: Optional product/SKU code
            currency_code: Currency code (default: EUR)
        """
        self.name = name.strip() if name else None
        self.description = description.strip() if description else None
        self.category = category
        self.quantity = Decimal(str(quantity))
        self.unit_price = Decimal(str(unit_price))
        self.total_amount = self.quantity * self.unit_price
        self.currency_code = currency_code
        self.billable = billable
        self.sku = sku.strip() if sku else None
        self.stock_item_id = stock_item_id
        self.created_by = created_by
        self.project_id = project_id
        self.invoice_id = invoice_id
    
    def __repr__(self):
        return f'<ExtraGood {self.name} ({self.quantity} x {self.unit_price} {self.currency_code})>'
    
    def update_total(self):
        """Recalculate total amount based on quantity and unit price"""
        self.total_amount = self.quantity * self.unit_price
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert extra good to dictionary for API responses"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'invoice_id': self.invoice_id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price),
            'total_amount': float(self.total_amount),
            'currency_code': self.currency_code,
            'billable': self.billable,
            'sku': self.sku,
            'stock_item_id': self.stock_item_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'creator': self.creator.username if self.creator else None
        }
    
    @classmethod
    def get_project_goods(cls, project_id, billable_only=False):
        """Get all extra goods for a specific project"""
        query = cls.query.filter_by(project_id=project_id)
        
        if billable_only:
            query = query.filter_by(billable=True)
        
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_invoice_goods(cls, invoice_id):
        """Get all extra goods for a specific invoice"""
        return cls.query.filter_by(invoice_id=invoice_id).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_total_amount(cls, project_id=None, invoice_id=None, billable_only=False):
        """Calculate total amount for goods with optional filters"""
        query = db.session.query(db.func.sum(cls.total_amount))
        
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        if invoice_id:
            query = query.filter_by(invoice_id=invoice_id)
        
        if billable_only:
            query = query.filter_by(billable=True)
        
        total = query.scalar() or Decimal('0')
        return float(total)
    
    @classmethod
    def get_goods_by_category(cls, project_id=None, invoice_id=None):
        """Get goods grouped by category"""
        query = db.session.query(
            cls.category,
            db.func.sum(cls.total_amount).label('total_amount'),
            db.func.count(cls.id).label('count')
        )
        
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        if invoice_id:
            query = query.filter_by(invoice_id=invoice_id)
        
        results = query.group_by(cls.category).all()
        
        return [
            {
                'category': category,
                'total_amount': float(total_amount),
                'count': count
            }
            for category, total_amount, count in results
        ]

