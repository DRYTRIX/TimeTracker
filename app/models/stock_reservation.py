"""StockReservation model for reserving stock"""
from datetime import datetime, timedelta
from decimal import Decimal
from app import db


class StockReservation(db.Model):
    """StockReservation model - reserves stock for quotes/invoices/projects"""
    
    __tablename__ = 'stock_reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_item_id = db.Column(db.Integer, db.ForeignKey('stock_items.id'), nullable=False, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False, index=True)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    reservation_type = db.Column(db.String(20), nullable=False, index=True)  # 'quote', 'invoice', 'project'
    reservation_id = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='reserved')  # 'reserved', 'fulfilled', 'cancelled', 'expired'
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    reserved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    reserved_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fulfilled_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    reserved_by_user = db.relationship('User', foreign_keys=[reserved_by])
    
    # Composite index for reservation lookups
    __table_args__ = (
        db.Index('ix_stock_reservations_reservation', 'reservation_type', 'reservation_id'),
    )
    
    def __init__(self, stock_item_id, warehouse_id, quantity, reservation_type, reservation_id,
                 reserved_by, expires_at=None, notes=None):
        self.stock_item_id = stock_item_id
        self.warehouse_id = warehouse_id
        self.quantity = Decimal(str(quantity))
        self.reservation_type = reservation_type
        self.reservation_id = reservation_id
        self.reserved_by = reserved_by
        self.expires_at = expires_at
        self.notes = notes.strip() if notes else None
        self.status = 'reserved'
    
    def __repr__(self):
        return f'<StockReservation {self.reservation_type} {self.reservation_id}: {self.quantity}>'
    
    @property
    def is_expired(self):
        """Check if reservation has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at and self.status == 'reserved'
    
    def fulfill(self):
        """Mark reservation as fulfilled"""
        if self.status != 'reserved':
            raise ValueError(f"Cannot fulfill reservation with status: {self.status}")
        self.status = 'fulfilled'
        self.fulfilled_at = datetime.utcnow()
        
        # Release reserved quantity from warehouse stock
        from .warehouse_stock import WarehouseStock
        stock = WarehouseStock.query.filter_by(
            warehouse_id=self.warehouse_id,
            stock_item_id=self.stock_item_id
        ).first()
        if stock:
            stock.release_reservation(self.quantity)
    
    def cancel(self):
        """Cancel the reservation"""
        if self.status not in ('reserved', 'expired'):
            raise ValueError(f"Cannot cancel reservation with status: {self.status}")
        
        # Release reserved quantity from warehouse stock
        from .warehouse_stock import WarehouseStock
        stock = WarehouseStock.query.filter_by(
            warehouse_id=self.warehouse_id,
            stock_item_id=self.stock_item_id
        ).first()
        if stock:
            stock.release_reservation(self.quantity)
        
        self.status = 'cancelled'
        self.cancelled_at = datetime.utcnow()
    
    def expire(self):
        """Mark reservation as expired"""
        if self.status != 'reserved':
            return
        
        # Release reserved quantity from warehouse stock
        from .warehouse_stock import WarehouseStock
        stock = WarehouseStock.query.filter_by(
            warehouse_id=self.warehouse_id,
            stock_item_id=self.stock_item_id
        ).first()
        if stock:
            stock.release_reservation(self.quantity)
        
        self.status = 'expired'
    
    @classmethod
    def create_reservation(cls, stock_item_id, warehouse_id, quantity, reservation_type,
                          reservation_id, reserved_by, expires_in_days=30, notes=None):
        """
        Create a stock reservation and update warehouse stock
        
        Returns:
            tuple: (StockReservation instance, updated WarehouseStock instance)
        """
        from .warehouse_stock import WarehouseStock
        
        # Calculate expiration date
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Get or create warehouse stock record
        stock = WarehouseStock.query.filter_by(
            warehouse_id=warehouse_id,
            stock_item_id=stock_item_id
        ).first()
        
        if not stock:
            stock = WarehouseStock(
                warehouse_id=warehouse_id,
                stock_item_id=stock_item_id,
                quantity_on_hand=0
            )
            db.session.add(stock)
        
        # Check available quantity
        available = stock.quantity_available
        if Decimal(str(quantity)) > available:
            raise ValueError(f"Insufficient stock. Available: {available}, Requested: {quantity}")
        
        # Create reservation
        reservation = cls(
            stock_item_id=stock_item_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            reservation_type=reservation_type,
            reservation_id=reservation_id,
            reserved_by=reserved_by,
            expires_at=expires_at,
            notes=notes
        )
        
        # Reserve quantity in warehouse stock
        stock.reserve(quantity)
        
        db.session.add(reservation)
        
        return reservation, stock
    
    def to_dict(self):
        """Convert stock reservation to dictionary"""
        return {
            'id': self.id,
            'stock_item_id': self.stock_item_id,
            'warehouse_id': self.warehouse_id,
            'quantity': float(self.quantity),
            'reservation_type': self.reservation_type,
            'reservation_id': self.reservation_id,
            'status': self.status,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'reserved_by': self.reserved_by,
            'reserved_at': self.reserved_at.isoformat() if self.reserved_at else None,
            'fulfilled_at': self.fulfilled_at.isoformat() if self.fulfilled_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'notes': self.notes,
            'is_expired': self.is_expired
        }

