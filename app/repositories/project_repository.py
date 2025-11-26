"""
Repository for project data access operations.
"""

from typing import List, Optional
from sqlalchemy.orm import joinedload
from app import db
from app.models import Project, Client
from app.repositories.base_repository import BaseRepository
from app.constants import ProjectStatus


class ProjectRepository(BaseRepository[Project]):
    """Repository for project operations"""
    
    def __init__(self):
        super().__init__(Project)
    
    def get_active_projects(
        self,
        user_id: Optional[int] = None,
        client_id: Optional[int] = None,
        include_relations: bool = False
    ) -> List[Project]:
        """Get active projects with optional filters"""
        query = self.model.query.filter_by(status=ProjectStatus.ACTIVE.value)
        
        if client_id:
            query = query.filter_by(client_id=client_id)
        
        if include_relations:
            # Only eagerly load client (time_entries is dynamic, can't be eagerly loaded)
            query = query.options(joinedload(Project.client_obj))
        
        # If user_id provided, filter projects user has access to
        # (This would need permission logic in a real implementation)
        
        return query.order_by(Project.name).all()
    
    def get_by_client(
        self,
        client_id: int,
        status: Optional[str] = None,
        include_relations: bool = False
    ) -> List[Project]:
        """Get projects for a client"""
        query = self.model.query.filter_by(client_id=client_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if include_relations:
            query = query.options(joinedload(Project.client_obj))
        
        return query.order_by(Project.name).all()
    
    def get_with_stats(
        self,
        project_id: int
    ) -> Optional[Project]:
        """Get project with related statistics (time entries, costs, etc.)"""
        # Note: time_entries, tasks, and costs are dynamic relationships (lazy='dynamic'),
        # so they cannot be eagerly loaded with joinedload(). They return query objects
        # that can be filtered and accessed when needed.
        return self.model.query.options(
            joinedload(Project.client_obj)
        ).get(project_id)
    
    def archive(self, project_id: int, archived_by: int, reason: Optional[str] = None) -> Optional[Project]:
        """Archive a project"""
        from datetime import datetime
        
        project = self.get_by_id(project_id)
        if project:
            project.status = ProjectStatus.ARCHIVED.value
            project.archived_at = datetime.utcnow()
            project.archived_by = archived_by
            project.archived_reason = reason
            return project
        return None
    
    def unarchive(self, project_id: int) -> Optional[Project]:
        """Unarchive a project"""
        project = self.get_by_id(project_id)
        if project and project.status == ProjectStatus.ARCHIVED.value:
            project.status = ProjectStatus.ACTIVE.value
            project.archived_at = None
            project.archived_by = None
            project.archived_reason = None
            return project
        return None
    
    def get_billable_projects(self, client_id: Optional[int] = None) -> List[Project]:
        """Get billable projects"""
        query = self.model.query.filter_by(
            billable=True,
            status=ProjectStatus.ACTIVE.value
        )
        
        if client_id:
            query = query.filter_by(client_id=client_id)
        
        return query.order_by(Project.name).all()

