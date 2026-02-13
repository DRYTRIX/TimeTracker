"""
Base CRUD service to reduce code duplication across services.
Provides common CRUD operations with consistent error handling.

Optional use: extend this class when adding a new domain that has a repository
and simple CRUD needs. Existing domain services do not use it. See
docs/development/SERVICE_LAYER_AND_BASE_CRUD.md for the chosen service pattern.
"""

from typing import TypeVar, Generic, Optional, Dict, Any, List
from app import db
from app.utils.db import safe_commit
from app.utils.api_responses import error_response

ModelType = TypeVar("ModelType")
RepositoryType = TypeVar("RepositoryType")


class BaseCRUDService(Generic[ModelType, RepositoryType]):
    """
    Base service class providing common CRUD operations.

    Subclasses should set:
    - self.repository: The repository instance
    - self.model_name: Human-readable model name for error messages
    """

    def __init__(self, repository: RepositoryType, model_name: str = "Record"):
        """
        Initialize base CRUD service.

        Args:
            repository: Repository instance for data access
            model_name: Human-readable name for error messages
        """
        self.repository = repository
        self.model_name = model_name

    def get_by_id(self, record_id: int) -> Dict[str, Any]:
        """
        Get a record by ID.

        Args:
            record_id: The record ID

        Returns:
            dict with 'success', 'message', and record data
        """
        record = self.repository.get_by_id(record_id)

        if not record:
            return {"success": False, "message": f"{self.model_name} not found", "error": "not_found"}

        return {"success": True, "message": f"{self.model_name} retrieved successfully", "data": record}

    def create(self, **kwargs) -> Dict[str, Any]:
        """
        Create a new record.

        Args:
            **kwargs: Fields for the new record

        Returns:
            dict with 'success', 'message', and created record
        """
        try:
            record = self.repository.create(**kwargs)

            if not safe_commit(f"create_{self.model_name.lower()}", kwargs):
                return {
                    "success": False,
                    "message": f"Could not create {self.model_name.lower()} due to a database error",
                    "error": "database_error",
                }

            return {"success": True, "message": f"{self.model_name} created successfully", "data": record}
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating {self.model_name.lower()}: {str(e)}",
                "error": "creation_error",
            }

    def update(self, record_id: int, **kwargs) -> Dict[str, Any]:
        """
        Update an existing record.

        Args:
            record_id: The record ID
            **kwargs: Fields to update

        Returns:
            dict with 'success', 'message', and updated record
        """
        record = self.repository.get_by_id(record_id)

        if not record:
            return {"success": False, "message": f"{self.model_name} not found", "error": "not_found"}

        try:
            self.repository.update(record, **kwargs)

            if not safe_commit(f"update_{self.model_name.lower()}", {"record_id": record_id}):
                return {
                    "success": False,
                    "message": f"Could not update {self.model_name.lower()} due to a database error",
                    "error": "database_error",
                }

            return {"success": True, "message": f"{self.model_name} updated successfully", "data": record}
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating {self.model_name.lower()}: {str(e)}",
                "error": "update_error",
            }

    def delete(self, record_id: int) -> Dict[str, Any]:
        """
        Delete a record.

        Args:
            record_id: The record ID

        Returns:
            dict with 'success' and 'message'
        """
        record = self.repository.get_by_id(record_id)

        if not record:
            return {"success": False, "message": f"{self.model_name} not found", "error": "not_found"}

        try:
            if not self.repository.delete(record):
                return {
                    "success": False,
                    "message": f"Could not delete {self.model_name.lower()}",
                    "error": "delete_error",
                }

            if not safe_commit(f"delete_{self.model_name.lower()}", {"record_id": record_id}):
                return {
                    "success": False,
                    "message": f"Could not delete {self.model_name.lower()} due to a database error",
                    "error": "database_error",
                }

            return {"success": True, "message": f"{self.model_name} deleted successfully"}
        except Exception as e:
            return {
                "success": False,
                "message": f"Error deleting {self.model_name.lower()}: {str(e)}",
                "error": "delete_error",
            }

    def list_all(self, page: int = 1, per_page: int = 20, **filters) -> Dict[str, Any]:
        """
        List all records with pagination and optional filters.

        Args:
            page: Page number
            per_page: Records per page
            **filters: Filter criteria

        Returns:
            dict with 'success', 'data', 'pagination', and 'total'
        """
        try:
            query = self.repository.query()

            # Apply filters
            if filters:
                query = query.filter_by(**filters)

            # Paginate
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)

            return {"success": True, "data": pagination.items, "pagination": pagination, "total": pagination.total}
        except Exception as e:
            return {
                "success": False,
                "message": f"Error listing {self.model_name.lower()}: {str(e)}",
                "error": "list_error",
            }
