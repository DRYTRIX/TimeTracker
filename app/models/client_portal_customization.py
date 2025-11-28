"""
Client Portal Customization model
Allows branding and customization of the client portal
"""

from datetime import datetime
from app import db


class ClientPortalCustomization(db.Model):
    """Customization settings for client portal branding"""

    __tablename__ = "client_portal_customizations"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, unique=True, index=True)

    # Branding
    logo_url = db.Column(db.String(500), nullable=True)  # URL to custom logo
    logo_upload_path = db.Column(db.String(500), nullable=True)  # Path to uploaded logo file
    favicon_url = db.Column(db.String(500), nullable=True)
    
    # Colors
    primary_color = db.Column(db.String(7), nullable=True)  # Hex color code
    secondary_color = db.Column(db.String(7), nullable=True)
    accent_color = db.Column(db.String(7), nullable=True)
    
    # Typography
    font_family = db.Column(db.String(100), nullable=True)  # Custom font family
    heading_font = db.Column(db.String(100), nullable=True)
    
    # Custom CSS
    custom_css = db.Column(db.Text, nullable=True)  # Custom CSS rules
    custom_header_html = db.Column(db.Text, nullable=True)  # Custom header HTML
    custom_footer_html = db.Column(db.Text, nullable=True)  # Custom footer HTML
    
    # Portal title and description
    portal_title = db.Column(db.String(200), nullable=True)  # Custom portal title
    portal_description = db.Column(db.Text, nullable=True)
    welcome_message = db.Column(db.Text, nullable=True)
    
    # Features
    show_projects = db.Column(db.Boolean, default=True, nullable=False)
    show_invoices = db.Column(db.Boolean, default=True, nullable=False)
    show_time_entries = db.Column(db.Boolean, default=True, nullable=False)
    show_quotes = db.Column(db.Boolean, default=True, nullable=False)
    
    # Navigation
    custom_navigation_items = db.Column(db.JSON, nullable=True)  # Custom menu items
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    client = db.relationship("Client", backref=db.backref("portal_customization", uselist=False))

    def __repr__(self):
        return f"<ClientPortalCustomization client={self.client_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "logo_url": self.logo_url,
            "logo_upload_path": self.logo_upload_path,
            "favicon_url": self.favicon_url,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "accent_color": self.accent_color,
            "font_family": self.font_family,
            "heading_font": self.heading_font,
            "custom_css": self.custom_css,
            "custom_header_html": self.custom_header_html,
            "custom_footer_html": self.custom_footer_html,
            "portal_title": self.portal_title,
            "portal_description": self.portal_description,
            "welcome_message": self.welcome_message,
            "show_projects": self.show_projects,
            "show_invoices": self.show_invoices,
            "show_time_entries": self.show_time_entries,
            "show_quotes": self.show_quotes,
            "custom_navigation_items": self.custom_navigation_items,
        }

    def get_css_variables(self):
        """Generate CSS variables from customization"""
        variables = []
        if self.primary_color:
            variables.append(f"--portal-primary-color: {self.primary_color};")
        if self.secondary_color:
            variables.append(f"--portal-secondary-color: {self.secondary_color};")
        if self.accent_color:
            variables.append(f"--portal-accent-color: {self.accent_color};")
        if self.font_family:
            variables.append(f"--portal-font-family: {self.font_family};")
        if self.heading_font:
            variables.append(f"--portal-heading-font: {self.heading_font};")
        return "\n".join(variables)

