"""
Repository for recurring invoice data access.
"""

from typing import List, Optional

from app.models import RecurringInvoice
from app.repositories.base_repository import BaseRepository


class RecurringInvoiceRepository(BaseRepository[RecurringInvoice]):
    """Repository for RecurringInvoice operations."""

    def __init__(self):
        super().__init__(RecurringInvoice)

    def list_for_user(
        self,
        created_by: Optional[int] = None,
        is_admin: bool = False,
        is_active: Optional[bool] = None,
    ) -> List[RecurringInvoice]:
        """List recurring invoices, optionally filtered by creator and active status."""
        query = self.model.query
        if not is_admin and created_by is not None:
            query = query.filter_by(created_by=created_by)
        if is_active is True:
            query = query.filter_by(is_active=True)
        elif is_active is False:
            query = query.filter_by(is_active=False)
        return query.order_by(RecurringInvoice.next_run_date.asc()).all()
