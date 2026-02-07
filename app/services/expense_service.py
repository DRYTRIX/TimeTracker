"""
Service for expense business logic.
"""

from typing import Optional, Dict, Any, List
from datetime import date
from decimal import Decimal
from app import db
from app.repositories import ExpenseRepository, ProjectRepository
from app.models import Expense
from app.utils.db import safe_commit


class ExpenseService:
    """Service for expense operations"""

    def __init__(self):
        self.expense_repo = ExpenseRepository()
        self.project_repo = ProjectRepository()

    def create_expense(
        self,
        amount: Decimal,
        expense_date: date,
        created_by: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        category: Optional[str] = None,
        category_id: Optional[int] = None,
        billable: bool = False,
        reimbursable: bool = True,
        currency_code: Optional[str] = None,
        tax_amount: Optional[Decimal] = None,
        tax_rate: Optional[Decimal] = None,
        payment_method: Optional[str] = None,
        payment_date: Optional[date] = None,
        tags: Optional[str] = None,
        receipt_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new expense.

        Returns:
            dict with 'success', 'message', and 'expense' keys
        """
        # Validate project if provided
        if project_id:
            project = self.project_repo.get_by_id(project_id)
            if not project:
                return {"success": False, "message": "Invalid project", "error": "invalid_project"}

        # Validate amount
        if amount <= 0:
            return {"success": False, "message": "Amount must be greater than zero", "error": "invalid_amount"}

        # Use model directly for full field support
        from app.models import Expense

        expense = Expense(
            user_id=created_by,
            title=title or description or "Expense",
            category=category,
            amount=amount,
            expense_date=expense_date,
            description=description,
            project_id=project_id,
            client_id=client_id,
            currency_code=currency_code or "EUR",
            tax_amount=tax_amount or Decimal("0.00"),
            tax_rate=tax_rate or Decimal("0.00"),
            payment_method=payment_method,
            payment_date=payment_date,
            billable=billable,
            reimbursable=reimbursable,
            tags=tags,
            receipt_path=receipt_path,
        )

        db.session.add(expense)

        if not safe_commit("create_expense", {"project_id": project_id, "created_by": created_by}):
            return {
                "success": False,
                "message": "Could not create expense due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Expense created successfully", "expense": expense}

    def get_project_expenses(
        self, project_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Expense]:
        """Get expenses for a project"""
        return self.expense_repo.get_by_project(
            project_id=project_id, start_date=start_date, end_date=end_date, include_relations=True
        )

    def get_total_expenses(
        self,
        project_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        billable_only: bool = False,
    ) -> float:
        """Get total expense amount"""
        return self.expense_repo.get_total_amount(
            project_id=project_id, start_date=start_date, end_date=end_date, billable_only=billable_only
        )

    def list_expenses(
        self,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        is_admin: bool = False,
        page: int = 1,
        per_page: int = 50,
    ) -> Dict[str, Any]:
        """
        List expenses with filtering and pagination.
        Uses eager loading to prevent N+1 queries.

        Returns:
            dict with 'expenses' and 'pagination' keys
        """
        from sqlalchemy.orm import joinedload

        query = self.expense_repo.query()

        # Eagerly load relations to prevent N+1
        query = query.options(joinedload(Expense.project), joinedload(Expense.user), joinedload(Expense.client))

        # Permission filter - non-admins only see their expenses
        if not is_admin and user_id:
            query = query.filter(Expense.user_id == user_id)

        # Apply filters
        if project_id:
            query = query.filter(Expense.project_id == project_id)
        if client_id:
            query = query.filter(Expense.client_id == client_id)
        if status:
            query = query.filter(Expense.status == status)
        if category:
            query = query.filter(Expense.category == category)
        if start_date:
            query = query.filter(Expense.expense_date >= start_date)
        if end_date:
            query = query.filter(Expense.expense_date <= end_date)

        # Order and paginate
        query = query.order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {"expenses": pagination.items, "pagination": pagination}

    def update_expense(self, expense_id: int, user_id: int, is_admin: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Update an expense.

        Returns:
            dict with 'success', 'message', and 'expense' keys
        """
        expense = self.expense_repo.get_by_id(expense_id)
        if not expense:
            return {"success": False, "message": "Expense not found", "error": "not_found"}

        # Check permissions
        if not is_admin and expense.user_id != user_id:
            return {"success": False, "message": "Access denied", "error": "access_denied"}

        # Update fields
        for field in ("title", "description", "category", "currency_code", "payment_method", "status", "tags"):
            if field in kwargs:
                setattr(expense, field, kwargs[field])
        if "amount" in kwargs:
            expense.amount = kwargs["amount"]
        if "expense_date" in kwargs:
            expense.expense_date = kwargs["expense_date"]
        if "payment_date" in kwargs:
            expense.payment_date = kwargs["payment_date"]
        for bfield in ("billable", "reimbursable", "reimbursed", "invoiced"):
            if bfield in kwargs:
                setattr(expense, bfield, bool(kwargs[bfield]))

        if not safe_commit("update_expense", {"expense_id": expense_id, "user_id": user_id}):
            return {
                "success": False,
                "message": "Could not update expense due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Expense updated successfully", "expense": expense}

    def delete_expense(self, expense_id: int, user_id: int, is_admin: bool = False) -> Dict[str, Any]:
        """
        Delete (reject) an expense.

        Returns:
            dict with 'success' and 'message' keys
        """
        expense = self.expense_repo.get_by_id(expense_id)
        if not expense:
            return {"success": False, "message": "Expense not found", "error": "not_found"}

        # Check permissions
        if not is_admin and expense.user_id != user_id:
            return {"success": False, "message": "Access denied", "error": "access_denied"}

        # Soft delete by setting status to rejected
        expense.status = "rejected"

        if not safe_commit("delete_expense", {"expense_id": expense_id, "user_id": user_id}):
            return {
                "success": False,
                "message": "Could not delete expense due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Expense rejected successfully"}
