"""Webhook event dispatcher - integrates with Activity system to trigger webhooks"""
import logging
from typing import Dict, Any, Optional
from flask import current_app
from app import db
from app.models.webhook import Webhook
from app.utils.webhook_service import WebhookService

logger = logging.getLogger(__name__)


class WebhookDispatcher:
    """Dispatcher for triggering webhooks based on system events"""
    
    @staticmethod
    def dispatch_event(event_type: str, payload: Dict[str, Any], 
                      event_id: Optional[str] = None, 
                      user_id: Optional[int] = None):
        """Dispatch a webhook event to all active webhooks that subscribe to it
        
        Args:
            event_type: Event type (e.g., 'project.created')
            payload: Event payload dictionary
            event_id: Optional unique event ID for deduplication
            user_id: Optional user ID who triggered the event
        """
        try:
            # Find all active webhooks that subscribe to this event
            webhooks = Webhook.query.filter(
                Webhook.is_active == True
            ).all()
            
            triggered_count = 0
            
            for webhook in webhooks:
                if webhook.subscribes_to(event_type):
                    try:
                        WebhookService.deliver_webhook(
                            webhook=webhook,
                            event_type=event_type,
                            payload=payload,
                            event_id=event_id
                        )
                        triggered_count += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to deliver webhook {webhook.id} for event {event_type}: {e}",
                            exc_info=True
                        )
            
            if triggered_count > 0:
                logger.debug(f"Dispatched {event_type} to {triggered_count} webhook(s)")
                
        except Exception as e:
            logger.error(f"Error dispatching webhook event {event_type}: {e}", exc_info=True)
    
    @staticmethod
    def map_activity_to_event(action: str, entity_type: str) -> Optional[str]:
        """Map Activity action and entity_type to webhook event type
        
        Args:
            action: Activity action (e.g., 'created', 'updated')
            entity_type: Entity type (e.g., 'project', 'task')
            
        Returns:
            str: Webhook event type or None if not mappable
        """
        # Map common actions
        action_map = {
            'created': 'created',
            'updated': 'updated',
            'deleted': 'deleted',
            'archived': 'archived',
            'unarchived': 'unarchived',
            'started': 'started',
            'stopped': 'stopped',
            'completed': 'completed',
            'assigned': 'assigned',
            'status_changed': 'status_changed',
            'sent': 'sent',
            'paid': 'paid',
            'overdue': 'overdue',
        }
        
        mapped_action = action_map.get(action.lower())
        if not mapped_action:
            return None
        
        # Map entity types
        entity_map = {
            'project': 'project',
            'task': 'task',
            'time_entry': 'time_entry',
            'invoice': 'invoice',
            'client': 'client',
            'user': 'user',
            'comment': 'comment',
        }
        
        mapped_entity = entity_map.get(entity_type.lower())
        if not mapped_entity:
            return None
        
        return f"{mapped_entity}.{mapped_action}"
    
    @staticmethod
    def build_payload_from_activity(activity, additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build webhook payload from Activity record
        
        Args:
            activity: Activity model instance
            additional_data: Optional additional data to include
            
        Returns:
            dict: Webhook payload
        """
        payload = {
            'event_type': WebhookDispatcher.map_activity_to_event(activity.action, activity.entity_type),
            'timestamp': activity.created_at.isoformat() if activity.created_at else None,
            'user': {
                'id': activity.user_id,
                'username': activity.user.username if activity.user else None,
                'display_name': activity.user.display_name if activity.user and hasattr(activity.user, 'display_name') else None,
            },
            'entity': {
                'type': activity.entity_type,
                'id': activity.entity_id,
                'name': activity.entity_name,
            },
            'action': activity.action,
            'description': activity.description,
        }
        
        # Add extra_data if available
        if activity.extra_data:
            payload['data'] = activity.extra_data
        
        # Add additional data
        if additional_data:
            payload.update(additional_data)
        
        return payload
    
    @staticmethod
    def on_activity_logged(activity):
        """Callback to be called when an activity is logged
        
        This method should be called after Activity.log() to trigger webhooks
        
        Args:
            activity: Activity model instance that was just logged
        """
        try:
            # Map activity to webhook event type
            event_type = WebhookDispatcher.map_activity_to_event(activity.action, activity.entity_type)
            
            if not event_type:
                # Event type not mappable, skip
                return
            
            # Build payload
            payload = WebhookDispatcher.build_payload_from_activity(activity)
            
            # Dispatch webhook
            WebhookDispatcher.dispatch_event(
                event_type=event_type,
                payload=payload,
                event_id=f"activity_{activity.id}",
                user_id=activity.user_id
            )
            
        except Exception as e:
            logger.error(f"Error processing activity for webhook: {e}", exc_info=True)


def dispatch_webhook(event: str, data: Dict[str, Any], user_id: Optional[int] = None):
    """Convenience function to dispatch a webhook event
    
    This is a wrapper around WebhookDispatcher.dispatch_event() for simpler usage.
    
    Args:
        event: Event type (e.g., 'time_entry.created')
        data: Event payload dictionary
        user_id: Optional user ID who triggered the event
    """
    WebhookDispatcher.dispatch_event(
        event_type=event,
        payload=data,
        user_id=user_id
    )
