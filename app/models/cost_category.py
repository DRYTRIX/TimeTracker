"""Shared expense-category link for project costs and recurring project costs."""

from sqlalchemy.ext.declarative import declared_attr

from app import db


class ExpenseCategoryLinkMixin:
    """Links a cost record to an ExpenseCategory while keeping the legacy ``category`` string.

    The ``category`` string column stays for one more release. Writes fill both columns;
    reads prefer the linked category and fall back to the string.
    """

    @declared_attr
    def category_id(cls):
        return db.Column(
            db.Integer,
            db.ForeignKey("expense_categories.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        )

    @declared_attr
    def expense_category(cls):
        return db.relationship("ExpenseCategory", foreign_keys=[cls.category_id])

    @property
    def category_name(self):
        """Display name: the linked category's name, or the legacy string when nothing is linked."""
        if self.expense_category is not None:
            return self.expense_category.name
        return self.category

    def set_category(self, expense_category):
        """Point this record at ``expense_category`` and keep the legacy string in step."""
        self.expense_category = expense_category
        self.category_id = expense_category.id if expense_category is not None else None
        if expense_category is not None:
            self.category = expense_category.legacy_key

    def set_category_from_input(self, category_id=None, category=None):
        """Apply a category given as an id or as a string (code or name).

        Returns an error message, or None on success. A string that matches no category is
        stored as the legacy value only, so older API clients keep working.
        """
        from app.models.expense_category import ExpenseCategory

        if category_id not in (None, ""):
            try:
                category_id = int(category_id)
            except (TypeError, ValueError):
                return "Invalid category_id"
            expense_category = ExpenseCategory.query.get(category_id)
            if expense_category is None:
                return "Category not found"
            self.set_category(expense_category)
            return None

        value = (category or "").strip()
        if not value:
            return "Category is required"
        expense_category = ExpenseCategory.find_by_key(value)
        if expense_category is not None:
            self.set_category(expense_category)
        else:
            self.expense_category = None
            self.category_id = None
            self.category = value[:50]
        return None
