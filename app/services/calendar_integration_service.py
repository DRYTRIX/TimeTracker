"""
Service for calendar integration business logic.
"""

from typing import Optional, List, Dict, Any
from app import db
from app.models import CalendarIntegration, CalendarSyncEvent, TimeEntry
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent
from app.utils.timezone import now_in_app_timezone
import logging

logger = logging.getLogger(__name__)


class CalendarIntegrationService:
    """
    Service for calendar integration operations.
    """
    
    def create_integration(
        self,
        user_id: int,
        provider: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[Any] = None,
        calendar_id: Optional[str] = None,
        calendar_name: Optional[str] = None,
        sync_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a calendar integration.
        
        Returns:
            dict with 'success', 'message', and 'integration' keys
        """
        try:
            # Check if integration already exists for this user and provider
            existing = CalendarIntegration.query.filter_by(
                user_id=user_id,
                provider=provider,
                is_active=True
            ).first()
            
            if existing:
                # Update existing integration
                existing.access_token = access_token
                existing.refresh_token = refresh_token
                existing.token_expires_at = token_expires_at
                existing.calendar_id = calendar_id
                existing.calendar_name = calendar_name
                if sync_settings:
                    existing.sync_settings = sync_settings
                
                if not safe_commit('update_calendar_integration', {'integration_id': existing.id}):
                    return {
                        'success': False,
                        'message': 'Could not update integration due to a database error.'
                    }
                
                return {
                    'success': True,
                    'message': 'Calendar integration updated successfully.',
                    'integration': existing
                }
            
            integration = CalendarIntegration(
                user_id=user_id,
                provider=provider,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
                calendar_id=calendar_id,
                calendar_name=calendar_name,
                sync_settings=sync_settings or {},
                is_active=True
            )
            
            db.session.add(integration)
            if not safe_commit('create_calendar_integration', {'user_id': user_id, 'provider': provider}):
                return {
                    'success': False,
                    'message': 'Could not create integration due to a database error.'
                }
            
            return {
                'success': True,
                'message': 'Calendar integration created successfully.',
                'integration': integration
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating calendar integration: {e}")
            return {
                'success': False,
                'message': f'Error creating integration: {str(e)}'
            }
    
    def get_integration(self, integration_id: int) -> Optional[CalendarIntegration]:
        """Get an integration by ID"""
        return CalendarIntegration.query.get(integration_id)
    
    def get_user_integrations(
        self,
        user_id: int,
        provider: Optional[str] = None
    ) -> List[CalendarIntegration]:
        """Get all integrations for a user"""
        query = CalendarIntegration.query.filter_by(user_id=user_id, is_active=True)
        if provider:
            query = query.filter_by(provider=provider)
        return query.all()
    
    def sync_time_entry_to_calendar(
        self,
        integration_id: int,
        time_entry_id: int,
        calendar_event_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync a time entry to calendar.
        
        Returns:
            dict with 'success', 'message', and 'sync_event' keys
        """
        try:
            integration = CalendarIntegration.query.get(integration_id)
            if not integration or not integration.is_active:
                return {
                    'success': False,
                    'message': 'Integration not found or inactive.'
                }
            
            time_entry = TimeEntry.query.get(time_entry_id)
            if not time_entry:
                return {
                    'success': False,
                    'message': 'Time entry not found.'
                }
            
            # Create sync event
            sync_event = CalendarSyncEvent(
                integration_id=integration_id,
                event_type='time_entry_created',
                time_entry_id=time_entry_id,
                calendar_event_id=calendar_event_id,
                direction='to_calendar',
                status='pending'
            )
            
            db.session.add(sync_event)
            if not safe_commit('sync_time_entry', {'time_entry_id': time_entry_id}):
                return {
                    'success': False,
                    'message': 'Could not create sync event due to a database error.'
                }
            
            return {
                'success': True,
                'message': 'Sync event created successfully.',
                'sync_event': sync_event
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing time entry: {e}")
            return {
                'success': False,
                'message': f'Error syncing time entry: {str(e)}'
            }
    
    def update_sync_status(
        self,
        sync_event_id: int,
        status: str,
        calendar_event_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update sync event status.
        
        Returns:
            dict with 'success', 'message', and 'sync_event' keys
        """
        try:
            sync_event = CalendarSyncEvent.query.get(sync_event_id)
            if not sync_event:
                return {
                    'success': False,
                    'message': 'Sync event not found.'
                }
            
            sync_event.status = status
            sync_event.synced_at = now_in_app_timezone()
            
            if calendar_event_id:
                sync_event.calendar_event_id = calendar_event_id
            if error_message:
                sync_event.error_message = error_message
            
            # Update integration last sync
            integration = sync_event.integration
            integration.last_sync_at = now_in_app_timezone()
            integration.last_sync_status = status
            if error_message:
                integration.last_sync_error = error_message
            
            if not safe_commit('update_sync_status', {'sync_event_id': sync_event_id}):
                return {
                    'success': False,
                    'message': 'Could not update sync status due to a database error.'
                }
            
            if status == 'synced':
                emit_event(WebhookEvent.CALENDAR_SYNCED, {
                    'integration_id': integration.id,
                    'sync_event_id': sync_event.id,
                    'time_entry_id': sync_event.time_entry_id
                })
            
            return {
                'success': True,
                'message': 'Sync status updated successfully.',
                'sync_event': sync_event
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating sync status: {e}")
            return {
                'success': False,
                'message': f'Error updating sync status: {str(e)}'
            }
    
    def deactivate_integration(
        self,
        integration_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Deactivate a calendar integration.
        
        Returns:
            dict with 'success' and 'message' keys
        """
        try:
            integration = CalendarIntegration.query.get(integration_id)
            if not integration:
                return {
                    'success': False,
                    'message': 'Integration not found.'
                }
            
            if integration.user_id != user_id:
                return {
                    'success': False,
                    'message': 'You do not have permission to deactivate this integration.'
                }
            
            integration.is_active = False
            if not safe_commit('deactivate_integration', {'integration_id': integration_id}):
                return {
                    'success': False,
                    'message': 'Could not deactivate integration due to a database error.'
                }
            
            return {
                'success': True,
                'message': 'Integration deactivated successfully.'
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deactivating integration: {e}")
            return {
                'success': False,
                'message': f'Error deactivating integration: {str(e)}'
            }

