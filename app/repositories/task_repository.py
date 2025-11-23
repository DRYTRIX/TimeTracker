"""
Repository for task data access operations.
"""

from typing import List, Optional
from sqlalchemy.orm import joinedload
from app import db
from app.models import Task
from app.repositories.base_repository import BaseRepository
from app.constants import TaskStatus


class TaskRepository(BaseRepository[Task]):
    """Repository for task operations"""
    
    def __init__(self):
        super().__init__(Task)
    
    def get_by_project(
        self,
        project_id: int,
        status: Optional[str] = None,
        include_relations: bool = False
    ) -> List[Task]:
        """Get tasks for a project"""
        query = self.model.query.filter_by(project_id=project_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if include_relations:
            query = query.options(
                joinedload(Task.project),
                joinedload(Task.assignee) if hasattr(Task, 'assignee') else query
            )
        
        return query.order_by(Task.priority.desc(), Task.due_date.asc()).all()
    
    def get_by_assignee(
        self,
        assignee_id: int,
        status: Optional[str] = None,
        include_relations: bool = False
    ) -> List[Task]:
        """Get tasks assigned to a user"""
        query = self.model.query.filter_by(assignee_id=assignee_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if include_relations:
            query = query.options(joinedload(Task.project))
        
        return query.order_by(Task.priority.desc(), Task.due_date.asc()).all()
    
    def get_by_status(
        self,
        status: str,
        project_id: Optional[int] = None,
        include_relations: bool = False
    ) -> List[Task]:
        """Get tasks by status"""
        query = self.model.query.filter_by(status=status)
        
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        if include_relations:
            query = query.options(joinedload(Task.project))
        
        return query.order_by(Task.priority.desc(), Task.due_date.asc()).all()
    
    def get_overdue(self, include_relations: bool = False) -> List[Task]:
        """Get overdue tasks"""
        from datetime import date
        
        today = date.today()
        query = self.model.query.filter(
            Task.due_date < today,
            Task.status.notin_([TaskStatus.DONE.value, TaskStatus.CANCELLED.value])
        )
        
        if include_relations:
            query = query.options(joinedload(Task.project))
        
        return query.order_by(Task.due_date.asc()).all()

