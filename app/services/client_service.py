"""
Service for client business logic.
"""

from typing import Optional, Dict, Any, List
from decimal import Decimal
from app import db
from app.repositories import ClientRepository
from app.models import Client
from app.utils.db import safe_commit


class ClientService:
    """Service for client operations"""
    
    def __init__(self):
        self.client_repo = ClientRepository()
    
    def create_client(
        self,
        name: str,
        email: Optional[str] = None,
        company: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        default_hourly_rate: Optional[Decimal] = None,
        created_by: int
    ) -> Dict[str, Any]:
        """
        Create a new client.
        
        Returns:
            dict with 'success', 'message', and 'client' keys
        """
        # Check for duplicate name
        existing = self.client_repo.get_by_name(name)
        if existing:
            return {
                'success': False,
                'message': 'A client with this name already exists',
                'error': 'duplicate_client'
            }
        
        # Create client
        client = self.client_repo.create(
            name=name,
            email=email,
            company=company,
            phone=phone,
            address=address,
            default_hourly_rate=default_hourly_rate,
            status='active'
        )
        
        if not safe_commit('create_client', {'name': name, 'created_by': created_by}):
            return {
                'success': False,
                'message': 'Could not create client due to a database error',
                'error': 'database_error'
            }
        
        return {
            'success': True,
            'message': 'Client created successfully',
            'client': client
        }
    
    def update_client(
        self,
        client_id: int,
        user_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a client.
        
        Returns:
            dict with 'success', 'message', and 'client' keys
        """
        client = self.client_repo.get_by_id(client_id)
        
        if not client:
            return {
                'success': False,
                'message': 'Client not found',
                'error': 'not_found'
            }
        
        # Update fields
        self.client_repo.update(client, **kwargs)
        
        if not safe_commit('update_client', {'client_id': client_id, 'user_id': user_id}):
            return {
                'success': False,
                'message': 'Could not update client due to a database error',
                'error': 'database_error'
            }
        
        return {
            'success': True,
            'message': 'Client updated successfully',
            'client': client
        }
    
    def get_active_clients(self) -> List[Client]:
        """Get all active clients"""
        return self.client_repo.get_active_clients()

