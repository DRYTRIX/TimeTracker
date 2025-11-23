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
        project_id: int,
        amount: Decimal,
        description: str,
        expense_date: date,
        category_id: Optional[int] = None,
        billable: bool = False,
        receipt_path: Optional[str] = None,
        created_by: int
    ) -> Dict[str, Any]:
        """
        Create a new expense.
        
        Returns:
            dict with 'success', 'message', and 'expense' keys
        """
        # Validate project
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return {
                'success': False,
                'message': 'Invalid project',
                'error': 'invalid_project'
            }
        
        # Validate amount
        if amount <= 0:
            return {
                'success': False,
                'message': 'Amount must be greater than zero',
                'error': 'invalid_amount'
            }
        
        # Create expense
        expense = self.expense_repo.create(
            project_id=project_id,
            amount=amount,
            description=description,
            date=expense_date,
            category_id=category_id,
            billable=billable,
            receipt_path=receipt_path,
            created_by=created_by
        )
        
        if not safe_commit('create_expense', {'project_id': project_id, 'created_by': created_by}):
            return {
                'success': False,
                'message': 'Could not create expense due to a database error',
                'error': 'database_error'
            }
        
        return {
            'success': True,
            'message': 'Expense created successfully',
            'expense': expense
        }
    
    def get_project_expenses(
        self,
        project_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Expense]:
        """Get expenses for a project"""
        return self.expense_repo.get_by_project(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            include_relations=True
        )
    
    def get_total_expenses(
        self,
        project_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        billable_only: bool = False
    ) -> float:
        """Get total expense amount"""
        return self.expense_repo.get_total_amount(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            billable_only=billable_only
        )

