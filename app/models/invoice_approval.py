"""Invoice approval workflow models"""
from datetime import datetime
from app import db


class InvoiceApproval(db.Model):
    """Invoice approval workflow tracking"""
    
    __tablename__ = 'invoice_approvals'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    
    # Approval workflow
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    # Status: 'pending', 'approved', 'rejected', 'cancelled'
    
    # Approval stages (JSON array)
    # Each stage: {stage_number, approver_id, status, comments, approved_at, rejected_at}
    stages = db.Column(db.JSON, nullable=False, default=list)
    
    # Current stage
    current_stage = db.Column(db.Integer, default=0, nullable=False)
    total_stages = db.Column(db.Integer, default=1, nullable=False)
    
    # Requester
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Final approval/rejection
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    invoice = db.relationship('Invoice', backref='approvals')
    requester = db.relationship('User', foreign_keys=[requested_by], backref='requested_approvals')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_invoices')
    rejector = db.relationship('User', foreign_keys=[rejected_by], backref='rejected_invoices')
    
    def __repr__(self):
        return f'<InvoiceApproval invoice_id={self.invoice_id} status={self.status}>'
    
    @property
    def is_pending(self):
        """Check if approval is pending"""
        return self.status == 'pending'
    
    @property
    def is_approved(self):
        """Check if approval is approved"""
        return self.status == 'approved'
    
    @property
    def is_rejected(self):
        """Check if approval is rejected"""
        return self.status == 'rejected'
    
    def to_dict(self):
        """Convert approval to dictionary"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'status': self.status,
            'stages': self.stages or [],
            'current_stage': self.current_stage,
            'total_stages': self.total_stages,
            'requested_by': self.requested_by,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejected_by': self.rejected_by,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'rejection_reason': self.rejection_reason,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

