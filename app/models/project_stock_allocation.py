"""ProjectStockAllocation model for tracking stock allocated to projects"""
from datetime import datetime
from decimal import Decimal
from app import db


class ProjectStockAllocation(db.Model):
    """ProjectStockAllocation model - tracks stock items allocated to projects"""
    
    __tablename__ = 'project_stock_allocations'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    stock_item_id = db.Column(db.Integer, db.ForeignKey('stock_items.id', ondelete='CASCADE'), nullable=False, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False, index=True)
    quantity_allocated = db.Column(db.Numeric(10, 2), nullable=False)
    quantity_used = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    allocated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    allocated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    project = db.relationship('Project', backref='stock_allocations')
    stock_item = db.relationship('StockItem', backref='project_allocations')
    warehouse = db.relationship('Warehouse', backref='project_allocations')
    allocated_by_user = db.relationship('User', foreign_keys=[allocated_by])
    
    def __init__(self, project_id, stock_item_id, warehouse_id, quantity_allocated, allocated_by, notes=None):
        self.project_id = project_id
        self.stock_item_id = stock_item_id
        self.warehouse_id = warehouse_id
        self.quantity_allocated = Decimal(str(quantity_allocated))
        self.allocated_by = allocated_by
        self.quantity_used = Decimal('0')
        self.notes = notes.strip() if notes else None
    
    def __repr__(self):
        return f'<ProjectStockAllocation {self.project_id}/{self.stock_item_id}: {self.quantity_allocated}>'
    
    @property
    def quantity_remaining(self):
        """Calculate remaining allocated quantity"""
        return self.quantity_allocated - self.quantity_used
    
    def record_usage(self, quantity):
        """Record usage of allocated stock"""
        qty = Decimal(str(quantity))
        if qty > self.quantity_remaining:
            raise ValueError(f"Cannot use more than allocated. Remaining: {self.quantity_remaining}, Requested: {qty}")
        self.quantity_used += qty
    
    def to_dict(self):
        """Convert project stock allocation to dictionary"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'stock_item_id': self.stock_item_id,
            'warehouse_id': self.warehouse_id,
            'quantity_allocated': float(self.quantity_allocated),
            'quantity_used': float(self.quantity_used),
            'quantity_remaining': float(self.quantity_remaining),
            'allocated_by': self.allocated_by,
            'allocated_at': self.allocated_at.isoformat() if self.allocated_at else None,
            'notes': self.notes
        }

