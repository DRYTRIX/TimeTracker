"""
Repository for expense data access operations.
"""

from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import joinedload
from app import db
from app.models import Expense
from app.repositories.base_repository import BaseRepository


class ExpenseRepository(BaseRepository[Expense]):
    """Repository for expense operations"""

    def __init__(self):
        super().__init__(Expense)

    def get_by_project(
        self,
        project_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_relations: bool = False,
    ) -> List[Expense]:
        """Get expenses for a project"""
        query = self.model.query.filter_by(project_id=project_id)

        if start_date:
            query = query.filter(Expense.expense_date >= start_date)

        if end_date:
            query = query.filter(Expense.expense_date <= end_date)

        if include_relations:
            query = query.options(
                joinedload(Expense.project), joinedload(Expense.category) if hasattr(Expense, "category") else query
            )

        return query.order_by(Expense.expense_date.desc()).all()

    def get_billable(
        self, project_id: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Expense]:
        """Get billable expenses"""
        query = self.model.query.filter_by(billable=True)

        if project_id:
            query = query.filter_by(project_id=project_id)

        if start_date:
            query = query.filter(Expense.expense_date >= start_date)

        if end_date:
            query = query.filter(Expense.expense_date <= end_date)

        return query.order_by(Expense.expense_date.desc()).all()

    def get_total_amount(
        self,
        project_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        billable_only: bool = False,
    ) -> float:
        """Get total expense amount"""
        from sqlalchemy import func

        query = db.session.query(func.sum(Expense.amount))

        if project_id:
            query = query.filter_by(project_id=project_id)

        if start_date:
            query = query.filter(Expense.expense_date >= start_date)

        if end_date:
            query = query.filter(Expense.expense_date <= end_date)

        if billable_only:
            query = query.filter_by(billable=True)

        result = query.scalar()
        return float(result) if result else 0.0
