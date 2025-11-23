"""
Service for task business logic.
"""

from typing import Optional, Dict, Any, List
from app import db
from app.repositories import TaskRepository, ProjectRepository
from app.models import Task
from app.constants import TaskStatus
from app.utils.db import safe_commit


class TaskService:
    """Service for task operations"""
    
    def __init__(self):
        self.task_repo = TaskRepository()
        self.project_repo = ProjectRepository()
    
    def create_task(
        self,
        name: str,
        project_id: int,
        description: Optional[str] = None,
        assignee_id: Optional[int] = None,
        priority: str = 'medium',
        due_date: Optional[Any] = None,
        created_by: int
    ) -> Dict[str, Any]:
        """
        Create a new task.
        
        Returns:
            dict with 'success', 'message', and 'task' keys
        """
        # Validate project
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return {
                'success': False,
                'message': 'Invalid project',
                'error': 'invalid_project'
            }
        
        # Create task
        task = self.task_repo.create(
            name=name,
            project_id=project_id,
            description=description,
            assignee_id=assignee_id,
            priority=priority,
            due_date=due_date,
            status=TaskStatus.TODO.value,
            created_by=created_by
        )
        
        if not safe_commit('create_task', {'project_id': project_id, 'created_by': created_by}):
            return {
                'success': False,
                'message': 'Could not create task due to a database error',
                'error': 'database_error'
            }
        
        return {
            'success': True,
            'message': 'Task created successfully',
            'task': task
        }
    
    def update_task(
        self,
        task_id: int,
        user_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a task.
        
        Returns:
            dict with 'success', 'message', and 'task' keys
        """
        task = self.task_repo.get_by_id(task_id)
        
        if not task:
            return {
                'success': False,
                'message': 'Task not found',
                'error': 'not_found'
            }
        
        # Update fields
        self.task_repo.update(task, **kwargs)
        
        if not safe_commit('update_task', {'task_id': task_id, 'user_id': user_id}):
            return {
                'success': False,
                'message': 'Could not update task due to a database error',
                'error': 'database_error'
            }
        
        return {
            'success': True,
            'message': 'Task updated successfully',
            'task': task
        }
    
    def get_project_tasks(
        self,
        project_id: int,
        status: Optional[str] = None
    ) -> List[Task]:
        """Get tasks for a project"""
        return self.task_repo.get_by_project(
            project_id=project_id,
            status=status,
            include_relations=True
        )

