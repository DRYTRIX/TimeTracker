"""Invoice PDF Template Model

Stores PDF templates for different page sizes (A4, Letter, A3, etc.)
"""

from datetime import datetime
from app import db


class InvoicePDFTemplate(db.Model):
    """Model for storing invoice PDF templates by page size"""

    __tablename__ = "invoice_pdf_templates"

    id = db.Column(db.Integer, primary_key=True)
    page_size = db.Column(db.String(20), nullable=False, unique=True)  # A4, Letter, A3, Legal, A5, etc.
    template_html = db.Column(db.Text, nullable=True)  # Legacy HTML template (backward compatibility)
    template_css = db.Column(db.Text, nullable=True)  # Legacy CSS template (backward compatibility)
    design_json = db.Column(db.Text, nullable=True)  # Konva.js design state
    template_json = db.Column(db.Text, nullable=True)  # ReportLab template JSON (new format)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Standard page sizes and their dimensions in mm (for reference)
    PAGE_SIZES = {
        "A4": {"width": 210, "height": 297},
        "Letter": {"width": 216, "height": 279},
        "Legal": {"width": 216, "height": 356},
        "A3": {"width": 297, "height": 420},
        "A5": {"width": 148, "height": 210},
        "Tabloid": {"width": 279, "height": 432},
    }

    def __repr__(self):
        return f"<InvoicePDFTemplate {self.page_size}>"

    @classmethod
    def get_template(cls, page_size="A4"):
        """Get template for a specific page size, create default if doesn't exist"""
        template = cls.query.filter_by(page_size=page_size).first()
        if not template:
            # Create default template for this size with default JSON
            from app.utils.pdf_template_schema import get_default_template
            import json
            
            default_json = get_default_template(page_size)
            template = cls(
                page_size=page_size,
                template_html="",
                template_css="",
                design_json="",
                template_json=json.dumps(default_json),
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
        
        # DON'T call ensure_template_json() here - it may overwrite saved templates
        # Only validate that template exists - if it has no JSON, it will be handled during export
        # This prevents overwriting saved custom templates with defaults
        return template

    @classmethod
    def get_all_templates(cls):
        """Get all templates ordered by page size"""
        return cls.query.order_by(cls.page_size).all()

    @classmethod
    def get_default_template(cls):
        """Get the default template (A4)"""
        return cls.get_template("A4")

    @classmethod
    def ensure_default_templates(cls):
        """Ensure all default templates exist"""
        from app.utils.pdf_template_schema import get_default_template
        import json
        
        default_sizes = ["A4", "Letter", "Legal", "A3", "A5"]
        for size in default_sizes:
            template = cls.query.filter_by(page_size=size).first()
            if not template:
                default_json = get_default_template(size)
                template = cls(
                    page_size=size,
                    template_html="",
                    template_css="",
                    design_json="",
                    template_json=json.dumps(default_json),
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
            "id": self.id,
            "page_size": self.page_size,
            "template_html": self.template_html or "",
            "template_css": self.template_css or "",
            "design_json": self.design_json or "",
            "template_json": self.template_json or "",
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_template_json(self):
        """Get template JSON, parsing from string if needed"""
        if not self.template_json:
            return None
        import json
        try:
            return json.loads(self.template_json)
        except Exception:
            return None
    
    def set_template_json(self, template_dict):
        """Set template JSON from dictionary"""
        import json
        self.template_json = json.dumps(template_dict) if template_dict else None

    def get_page_dimensions_mm(self):
        """Get page dimensions in mm"""
        return self.PAGE_SIZES.get(self.page_size, {"width": 210, "height": 297})

    def get_page_dimensions_px(self, dpi=72):
        """Get page dimensions in pixels at given DPI"""
        dims_mm = self.get_page_dimensions_mm()
        # Convert mm to pixels: 1 mm = (dpi / 25.4) pixels
        width_px = int((dims_mm["width"] / 25.4) * dpi)
        height_px = int((dims_mm["height"] / 25.4) * dpi)
        return {"width": width_px, "height": height_px}
    
    def ensure_template_json(self):
        """Ensure template has valid JSON, generate if missing"""
        from flask import current_app
        import json
        
        # First check if template_json exists and is not empty
        if self.template_json and self.template_json.strip():
            # Validate that it's valid JSON
            try:
                parsed_json = json.loads(self.template_json)
                # If it's valid JSON with at least a page property, consider it valid
                if isinstance(parsed_json, dict) and "page" in parsed_json:
                    current_app.logger.info(f"[TEMPLATE] Template JSON is valid - PageSize: '{self.page_size}', TemplateID: {self.id}")
                    return  # Template JSON is valid, don't overwrite
                else:
                    current_app.logger.warning(f"[TEMPLATE] Template JSON exists but missing 'page' property - PageSize: '{self.page_size}', TemplateID: {self.id}")
            except json.JSONDecodeError as e:
                current_app.logger.warning(f"[TEMPLATE] Template JSON exists but is invalid JSON - PageSize: '{self.page_size}', TemplateID: {self.id}, Error: {str(e)}")
                # Invalid JSON - will generate default below
        
        # Only generate default if template_json is truly None or empty, or invalid
        if not self.template_json or not self.template_json.strip():
            current_app.logger.warning(f"[TEMPLATE] Generating default template JSON - PageSize: '{self.page_size}', TemplateID: {self.id}, Reason: template_json is missing or empty")
        else:
            current_app.logger.warning(f"[TEMPLATE] Generating default template JSON - PageSize: '{self.page_size}', TemplateID: {self.id}, Reason: existing JSON is invalid")
        
        from app.utils.pdf_template_schema import get_default_template
        
        default_json = get_default_template(self.page_size)
        self.template_json = json.dumps(default_json)
        try:
            db.session.commit()
            current_app.logger.info(f"[TEMPLATE] Default template JSON saved - PageSize: '{self.page_size}', TemplateID: {self.id}")
        except Exception as e:
            current_app.logger.error(f"[TEMPLATE] Failed to save default template JSON - PageSize: '{self.page_size}', TemplateID: {self.id}, Error: {str(e)}", exc_info=True)
            db.session.rollback()
