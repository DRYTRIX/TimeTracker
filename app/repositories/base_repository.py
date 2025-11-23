"""
Base repository class providing common database operations.
"""

from typing import TypeVar, Generic, List, Optional, Dict, Any
from sqlalchemy.orm import Query
from app import db

ModelType = TypeVar('ModelType')


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, model: type[ModelType]):
        """
        Initialize repository with a model class.
        
        Args:
            model: SQLAlchemy model class
        """
        self.model = model
    
    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get a single record by ID"""
        return self.model.query.get(id)
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[ModelType]:
        """Get all records with optional pagination"""
        query = self.model.query
        if limit:
            query = query.limit(limit).offset(offset)
        return query.all()
    
    def find_by(self, **kwargs) -> List[ModelType]:
        """Find records by field values"""
        return self.model.query.filter_by(**kwargs).all()
    
    def find_one_by(self, **kwargs) -> Optional[ModelType]:
        """Find a single record by field values"""
        return self.model.query.filter_by(**kwargs).first()
    
    def create(self, **kwargs) -> ModelType:
        """Create a new record"""
        instance = self.model(**kwargs)
        db.session.add(instance)
        return instance
    
    def update(self, instance: ModelType, **kwargs) -> ModelType:
        """Update an existing record"""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance
    
    def delete(self, instance: ModelType) -> bool:
        """Delete a record"""
        try:
            db.session.delete(instance)
            return True
        except Exception:
            return False
    
    def count(self, **kwargs) -> int:
        """Count records matching criteria"""
        query = self.model.query
        if kwargs:
            query = query.filter_by(**kwargs)
        return query.count()
    
    def exists(self, **kwargs) -> bool:
        """Check if a record exists"""
        return self.model.query.filter_by(**kwargs).first() is not None
    
    def query(self) -> Query:
        """Get a query object for custom queries"""
        return self.model.query

