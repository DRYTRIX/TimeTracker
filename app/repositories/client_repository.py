"""
Repository for client data access operations.
"""

from typing import List, Optional

from app.models import Client
from app.repositories.base_repository import BaseRepository


class ClientRepository(BaseRepository[Client]):
    """Repository for client operations"""

    def __init__(self):
        super().__init__(Client)

    def get_with_projects(self, client_id: int) -> Optional[Client]:
        """Get client by id.

        ``Client.projects`` is ``lazy='dynamic'`` and cannot be eager-loaded
        with joinedload (Issue #716). Callers that need projects should use
        ``client.projects.all()`` or a separate query.
        """
        return self.get_by_id(client_id)

    def get_active_clients(self) -> List[Client]:
        """Get all active clients"""
        return self.model.query.filter_by(status="active").order_by(Client.name).all()

    def get_by_name(self, name: str) -> Optional[Client]:
        """Get client by name"""
        return self.model.query.filter_by(name=name).first()
