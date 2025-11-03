"""Invoice PDF Template Model

Stores PDF templates for different page sizes (A4, Letter, A3, etc.)
"""
from datetime import datetime
from app import db


class InvoicePDFTemplate(db.Model):
    """Model for storing invoice PDF templates by page size"""
    
    __tablename__ = 'invoice_pdf_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    page_size = db.Column(db.String(20), nullable=False, unique=True)  # A4, Letter, A3, Legal, A5, etc.
    template_html = db.Column(db.Text, nullable=True)
    template_css = db.Column(db.Text, nullable=True)
    design_json = db.Column(db.Text, nullable=True)  # Konva.js design state
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Standard page sizes and their dimensions in mm (for reference)
    PAGE_SIZES = {
        'A4': {'width': 210, 'height': 297},
        'Letter': {'width': 216, 'height': 279},
        'Legal': {'width': 216, 'height': 356},
        'A3': {'width': 297, 'height': 420},
        'A5': {'width': 148, 'height': 210},
        'Tabloid': {'width': 279, 'height': 432},
    }
    
    def __repr__(self):
        return f'<InvoicePDFTemplate {self.page_size}>'
    
    @classmethod
    def get_template(cls, page_size='A4'):
        """Get template for a specific page size, create default if doesn't exist"""
        template = cls.query.filter_by(page_size=page_size).first()
        if not template:
            # Create default template for this size
            template = cls(
                page_size=page_size,
                template_html='',
                template_css='',
                design_json='',
                is_default=True
            )
            db.session.add(template)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                # Try to get again in case it was created concurrently
                template = cls.query.filter_by(page_size=page_size).first()
                if not template:
                    raise
        return template
    
    @classmethod
    def get_all_templates(cls):
        """Get all templates ordered by page size"""
        return cls.query.order_by(cls.page_size).all()
    
    @classmethod
    def get_default_template(cls):
        """Get the default template (A4)"""
        return cls.get_template('A4')
    
    @classmethod
    def ensure_default_templates(cls):
        """Ensure all default templates exist"""
        default_sizes = ['A4', 'Letter', 'Legal', 'A3', 'A5']
        for size in default_sizes:
            template = cls.query.filter_by(page_size=size).first()
            if not template:
                template = cls(
                    page_size=size,
                    template_html='',
                    template_css='',
                    design_json='',
                    is_default=True
                )
                db.session.add(template)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    
    def to_dict(self):
        """Convert template to dictionary"""
        return {
            'id': self.id,
            'page_size': self.page_size,
            'template_html': self.template_html or '',
            'template_css': self.template_css or '',
            'design_json': self.design_json or '',
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_page_dimensions_mm(self):
        """Get page dimensions in mm"""
        return self.PAGE_SIZES.get(self.page_size, {'width': 210, 'height': 297})
    
    def get_page_dimensions_px(self, dpi=72):
        """Get page dimensions in pixels at given DPI"""
        dims_mm = self.get_page_dimensions_mm()
        # Convert mm to pixels: 1 mm = (dpi / 25.4) pixels
        width_px = int((dims_mm['width'] / 25.4) * dpi)
        height_px = int((dims_mm['height'] / 25.4) * dpi)
        return {'width': width_px, 'height': height_px}

