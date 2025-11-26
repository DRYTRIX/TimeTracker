"""
Service for project template business logic.
"""

from typing import Optional, List, Dict, Any
from app import db
from app.models import ProjectTemplate, Project, Task, User
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent


class ProjectTemplateService:
    """
    Service for project template operations.
    """
    
    def create_template(
        self,
        name: str,
        created_by: int,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        tasks: Optional[List[Dict[str, Any]]] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_public: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new project template.
        
        Returns:
            dict with 'success', 'message', and 'template' keys
        """
        try:
            template = ProjectTemplate(
                name=name,
                description=description,
                config=config or {},
                tasks=tasks or [],
                category=category,
                tags=tags or [],
                is_public=is_public,
                created_by=created_by
            )
            
            db.session.add(template)
            if not safe_commit('create_template', {'name': name}):
                return {
                    'success': False,
                    'message': 'Could not create template due to a database error.'
                }
            
            emit_event(WebhookEvent.PROJECT_TEMPLATE_CREATED, {
                'template_id': template.id,
                'template_name': template.name,
                'created_by': created_by
            })
            
            return {
                'success': True,
                'message': 'Template created successfully.',
                'template': template
            }
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error creating template: {str(e)}'
            }
    
    def create_project_from_template(
        self,
        template_id: int,
        client_id: int,
        created_by: int,
        name: Optional[str] = None,
        override_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a project from a template.
        
        Returns:
            dict with 'success', 'message', and 'project' keys
        """
        try:
            template = ProjectTemplate.query.get(template_id)
            if not template:
                return {
                    'success': False,
                    'message': 'Template not found.'
                }
            
            # Merge template config with overrides
            config = template.config.copy()
            if override_config:
                config.update(override_config)
            
            # Use provided name or template name
            project_name = name or template.name
            
            # Create project
            from app.services.project_service import ProjectService
            project_service = ProjectService()
            
            result = project_service.create_project(
                name=project_name,
                client_id=client_id,
                description=config.get('description', template.description),
                billable=config.get('billable', True),
                hourly_rate=config.get('hourly_rate'),
                created_by=created_by
            )
            
            if not result['success']:
                return result
            
            project = result['project']
            
            # Apply additional config
            if 'billing_ref' in config:
                project.billing_ref = config['billing_ref']
            if 'code' in config:
                project.code = config['code']
            if 'estimated_hours' in config:
                project.estimated_hours = config['estimated_hours']
            if 'budget_amount' in config:
                project.budget_amount = config['budget_amount']
            if 'budget_threshold_percent' in config:
                project.budget_threshold_percent = config['budget_threshold_percent']
            
            # Create tasks from template
            if template.tasks:
                from app.services.task_service import TaskService
                task_service = TaskService()
                
                for task_config in template.tasks:
                    task_service.create_task(
                        name=task_config.get('name', 'Untitled Task'),
                        project_id=project.id,
                        description=task_config.get('description'),
                        priority=task_config.get('priority', 'medium'),
                        status=task_config.get('status', 'todo'),
                        estimated_hours=task_config.get('estimated_hours'),
                        created_by=created_by
                    )
            
            # Update template usage
            template.usage_count += 1
            from app.utils.timezone import now_in_app_timezone
            template.last_used_at = now_in_app_timezone()
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Project created from template successfully.',
                'project': project
            }
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error creating project from template: {str(e)}'
            }
    
    def get_template(self, template_id: int) -> Optional[ProjectTemplate]:
        """Get a template by ID"""
        return ProjectTemplate.query.get(template_id)
    
    def list_templates(
        self,
        user_id: Optional[int] = None,
        category: Optional[str] = None,
        is_public: Optional[bool] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Any:  # Returns pagination object from query.paginate()
        """
        List templates with filtering and pagination.
        
        Returns:
            Pagination object with templates
        """
        query = ProjectTemplate.query
        
        # Filter by user (own templates or public)
        if user_id:
            query = query.filter(
                db.or_(
                    ProjectTemplate.created_by == user_id,
                    ProjectTemplate.is_public == True
                )
            )
        elif is_public is not None:
            query = query.filter(ProjectTemplate.is_public == is_public)
        
        # Filter by category
        if category:
            query = query.filter(ProjectTemplate.category == category)
        
        # Order by usage count and name
        query = query.order_by(
            ProjectTemplate.usage_count.desc(),
            ProjectTemplate.name.asc()
        )
        
        return query.paginate(page=page, per_page=per_page, error_out=False)
    
    def update_template(
        self,
        template_id: int,
        user_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a template.
        
        Returns:
            dict with 'success' and 'message' keys
        """
        try:
            template = ProjectTemplate.query.get(template_id)
            if not template:
                return {
                    'success': False,
                    'message': 'Template not found.'
                }
            
            # Check permissions
            if template.created_by != user_id:
                return {
                    'success': False,
                    'message': 'You do not have permission to edit this template.'
                }
            
            # Update fields
            if 'name' in kwargs:
                template.name = kwargs['name']
            if 'description' in kwargs:
                template.description = kwargs['description']
            if 'config' in kwargs:
                template.config = kwargs['config']
            if 'tasks' in kwargs:
                template.tasks = kwargs['tasks']
            if 'category' in kwargs:
                template.category = kwargs['category']
            if 'tags' in kwargs:
                template.tags = kwargs['tags']
            if 'is_public' in kwargs:
                template.is_public = kwargs['is_public']
            
            if not safe_commit('update_template', {'template_id': template_id}):
                return {
                    'success': False,
                    'message': 'Could not update template due to a database error.'
                }
            
            emit_event(WebhookEvent.PROJECT_TEMPLATE_UPDATED, {
                'template_id': template.id,
                'template_name': template.name
            })
            
            return {
                'success': True,
                'message': 'Template updated successfully.',
                'template': template
            }
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error updating template: {str(e)}'
            }
    
    def delete_template(
        self,
        template_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Delete a template.
        
        Returns:
            dict with 'success' and 'message' keys
        """
        try:
            template = ProjectTemplate.query.get(template_id)
            if not template:
                return {
                    'success': False,
                    'message': 'Template not found.'
                }
            
            # Check permissions
            if template.created_by != user_id:
                return {
                    'success': False,
                    'message': 'You do not have permission to delete this template.'
                }
            
            template_name = template.name
            db.session.delete(template)
            
            if not safe_commit('delete_template', {'template_id': template_id}):
                return {
                    'success': False,
                    'message': 'Could not delete template due to a database error.'
                }
            
            emit_event(WebhookEvent.PROJECT_TEMPLATE_DELETED, {
                'template_id': template_id,
                'template_name': template_name
            })
            
            return {
                'success': True,
                'message': 'Template deleted successfully.'
            }
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error deleting template: {str(e)}'
            }

