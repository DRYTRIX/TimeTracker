"""
Base repository class providing common database operations.

This module provides the base repository pattern implementation for data access.
All repositories should inherit from BaseRepository to get common CRUD operations.

Example:
    class ProjectRepository(BaseRepository[Project]):
        def __init__(self):
            super().__init__(Project)

        def get_active_projects(self):
            return self.model.query.filter_by(status='active').all()
"""

from typing import TypeVar, Generic, List, Optional, Dict, Any
from sqlalchemy.orm import Query
from app import db

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.

    Provides standard database operations that can be used by all repositories.
    Subclasses should add domain-specific query methods.

    Args:
        model: SQLAlchemy model class

    Example:
        repo = BaseRepository(Project)
        project = repo.get_by_id(1)
        projects = repo.find_by(status='active')
    """

    def __init__(self, model: type[ModelType]):
        """
        Initialize repository with a model class.

        Args:
            model: SQLAlchemy model class
        """
        self.model = model

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Get a single record by ID.

        Args:
            id: Record ID

        Returns:
            Model instance or None if not found
        """
        return self.model.query.get(id)

    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[ModelType]:
        """
        Get all records with optional pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of model instances
        """
        query = self.model.query
        if limit:
            query = query.limit(limit).offset(offset)
        return query.all()

    def find_by(self, **kwargs) -> List[ModelType]:
        """
        Find records by field values.

        Args:
            **kwargs: Field name-value pairs to filter by

        Returns:
            List of matching model instances
        """
        return self.model.query.filter_by(**kwargs).all()

    def find_one_by(self, **kwargs) -> Optional[ModelType]:
        """
        Find a single record by field values.

        Args:
            **kwargs: Field name-value pairs to filter by

        Returns:
            First matching model instance or None
        """
        return self.model.query.filter_by(**kwargs).first()

    def create(self, **kwargs) -> ModelType:
        """
        Create a new record.

        Args:
            **kwargs: Field name-value pairs for the new record

        Returns:
            Created model instance (not yet committed)
        """
        instance = self.model(**kwargs)
        db.session.add(instance)
        return instance

    def update(self, instance: ModelType, **kwargs) -> ModelType:
        """
        Update an existing record.

        Args:
            instance: Model instance to update
            **kwargs: Field name-value pairs to update

        Returns:
            Updated model instance
        """
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

    def delete(self, instance: ModelType) -> bool:
        """
        Delete a record.

        Args:
            instance: Model instance to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            db.session.delete(instance)
            return True
        except Exception:
            return False

    def count(self, **kwargs) -> int:
        """
        Count records matching criteria.

        Args:
            **kwargs: Field name-value pairs to filter by

        Returns:
            Number of matching records
        """
        query = self.model.query
        if kwargs:
            query = query.filter_by(**kwargs)
        return query.count()

    def exists(self, **kwargs) -> bool:
        """
        Check if a record exists.

        Args:
            **kwargs: Field name-value pairs to filter by

        Returns:
            True if at least one matching record exists
        """
        return self.model.query.filter_by(**kwargs).first() is not None

    def query(self) -> Query:
        """
        Get a query object for custom queries.

        Returns:
            SQLAlchemy Query object for the model
        """
        return self.model.query
