"""
Service for project business logic.
"""

from typing import Optional, List, Dict, Any
from app import db
from app.repositories import ProjectRepository, ClientRepository
from app.models import Project
from app.constants import ProjectStatus
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent


class ProjectService:
    """Service for project operations"""
    
    def __init__(self):
        self.project_repo = ProjectRepository()
        self.client_repo = ClientRepository()
    
    def create_project(
        self,
        name: str,
        client_id: int,
        description: Optional[str] = None,
        billable: bool = True,
        hourly_rate: Optional[float] = None,
        created_by: int
    ) -> Dict[str, Any]:
        """
        Create a new project.
        
        Returns:
            dict with 'success', 'message', and 'project' keys
        """
        # Validate client
        client = self.client_repo.get_by_id(client_id)
        if not client:
            return {
                'success': False,
                'message': 'Invalid client',
                'error': 'invalid_client'
            }
        
        # Check for duplicate name
        existing = self.project_repo.find_one_by(name=name, client_id=client_id)
        if existing:
            return {
                'success': False,
                'message': 'A project with this name already exists for this client',
                'error': 'duplicate_project'
            }
        
        # Create project
        project = self.project_repo.create(
            name=name,
            client_id=client_id,
            description=description,
            billable=billable,
            hourly_rate=hourly_rate,
            status=ProjectStatus.ACTIVE.value,
            created_by=created_by
        )
        
        if not safe_commit('create_project', {'client_id': client_id, 'name': name}):
            return {
                'success': False,
                'message': 'Could not create project due to a database error',
                'error': 'database_error'
            }
        
        # Emit domain event
        emit_event(WebhookEvent.PROJECT_CREATED.value, {
            'project_id': project.id,
            'client_id': client_id
        })
        
        return {
            'success': True,
            'message': 'Project created successfully',
            'project': project
        }
    
    def update_project(
        self,
        project_id: int,
        user_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a project.
        
        Returns:
            dict with 'success', 'message', and 'project' keys
        """
        project = self.project_repo.get_by_id(project_id)
        
        if not project:
            return {
                'success': False,
                'message': 'Project not found',
                'error': 'not_found'
            }
        
        # Update fields
        self.project_repo.update(project, **kwargs)
        
        if not safe_commit('update_project', {'project_id': project_id, 'user_id': user_id}):
            return {
                'success': False,
                'message': 'Could not update project due to a database error',
                'error': 'database_error'
            }
        
        return {
            'success': True,
            'message': 'Project updated successfully',
            'project': project
        }
    
    def archive_project(
        self,
        project_id: int,
        user_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Archive a project.
        
        Returns:
            dict with 'success', 'message', and 'project' keys
        """
        project = self.project_repo.archive(project_id, user_id, reason)
        
        if not project:
            return {
                'success': False,
                'message': 'Project not found',
                'error': 'not_found'
            }
        
        if not safe_commit('archive_project', {'project_id': project_id, 'user_id': user_id}):
            return {
                'success': False,
                'message': 'Could not archive project due to a database error',
                'error': 'database_error'
            }
        
        return {
            'success': True,
            'message': 'Project archived successfully',
            'project': project
        }
    
    def get_active_projects(self, user_id: Optional[int] = None, client_id: Optional[int] = None) -> List[Project]:
        """Get active projects with optional filters"""
        return self.project_repo.get_active_projects(
            user_id=user_id,
            client_id=client_id,
            include_relations=True
        )

