"""HTML invoice templates: written in the app or uploaded as an .html file.

A template is one HTML page with its own ``<style>``. It is rendered with Jinja in a
sandbox and turned into a PDF by WeasyPrint (see ``app/utils/invoice_pdf_html.py``).

Every successful save adds an ``InvoiceHtmlTemplateVersion``. Versions have no UI:
they exist so that an invoice that has left draft keeps printing with the exact
template it was issued with (``Invoice.pdf_template_version_id``).

Not to be confused with ``InvoiceTemplate``, which holds invoice *email* templates.
"""

from datetime import datetime

from sqlalchemy import event
from sqlalchemy.orm.base import NEVER_SET, NO_VALUE

from app import db

from .invoice import Invoice


class InvoiceHtmlTemplate(db.Model):
    __tablename__ = "invoice_html_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    html = db.Column(db.Text, nullable=False, default="")
    source = db.Column(db.String(20), nullable=False, default="created")  # created | uploaded | duplicated
    current_version_id = db.Column(
        db.Integer,
        db.ForeignKey("invoice_html_template_versions.id", use_alter=True, name="fk_invoice_html_tpl_current_version"),
        nullable=True,
    )
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    versions = db.relationship(
        "InvoiceHtmlTemplateVersion",
        backref="template",
        lazy="dynamic",
        foreign_keys="InvoiceHtmlTemplateVersion.template_id",
        order_by="InvoiceHtmlTemplateVersion.number",
    )
    current_version = db.relationship("InvoiceHtmlTemplateVersion", foreign_keys=[current_version_id], post_update=True)
    updater = db.relationship("User", foreign_keys=[updated_by])

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    @property
    def ref(self):
        """Reference used by Settings, legal entities and invoices: ``html:<id>``."""
        return f"html:{self.id}"

    @property
    def version_number(self):
        return self.current_version.number if self.current_version else 0

    @classmethod
    def active(cls):
        return cls.query.filter(cls.deleted_at.is_(None))

    @classmethod
    def name_taken(cls, name, exclude_id=None):
        q = cls.active().filter(db.func.lower(cls.name) == (name or "").strip().lower())
        if exclude_id:
            q = q.filter(cls.id != exclude_id)
        return db.session.query(q.exists()).scalar()

    @classmethod
    def free_name(cls, name):
        """``name`` if it is free, else ``name (2)``, ``name (3)``…"""
        base = (name or "").strip() or "template"
        if not cls.name_taken(base):
            return base
        n = 2
        while cls.name_taken(f"{base} ({n})"):
            n += 1
        return f"{base} ({n})"

    def save_version(self, user_id=None):
        """Add a version if the html differs from the current one. Returns the current version."""
        current = self.current_version
        if current is not None and current.html == self.html:
            return current
        number = (current.number if current else 0) + 1
        version = InvoiceHtmlTemplateVersion(template=self, number=number, html=self.html, created_by=user_id)
        db.session.add(version)
        db.session.flush()
        self.current_version_id = version.id
        self.current_version = version
        return version

    def __repr__(self):
        return f"<InvoiceHtmlTemplate {self.id} {self.name!r}>"


class InvoiceHtmlTemplateVersion(db.Model):
    __tablename__ = "invoice_html_template_versions"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer, db.ForeignKey("invoice_html_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    number = db.Column(db.Integer, nullable=False)
    html = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("template_id", "number", name="uq_invoice_html_tpl_version"),)

    def __repr__(self):
        return f"<InvoiceHtmlTemplateVersion {self.template_id}#{self.number}>"


def _freeze_template_when_leaving_draft(target, value, oldvalue, initiator):
    """``Invoice.status`` listener: the moment an invoice stops being a draft, fix its PDF template."""
    if value in (None, "draft"):
        return
    if oldvalue not in (None, "draft", NO_VALUE, NEVER_SET):
        return
    from app.utils.invoice_templates import freeze_invoice_template

    with db.session.no_autoflush:
        freeze_invoice_template(target)


event.listen(Invoice.status, "set", _freeze_template_when_leaving_draft)
