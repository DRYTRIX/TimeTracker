"""
Event bus for domain events.
Provides decoupled event-driven architecture.
"""

from functools import wraps
from typing import Any, Callable, Dict, List, Union

from flask import current_app

from app.constants import WebhookEvent

EventType = Union[str, WebhookEvent]


def _coerce_event_type(event_type: EventType) -> str:
    """Normalize an event type passed as ``str`` or ``WebhookEvent`` to ``str``."""
    if isinstance(event_type, WebhookEvent):
        return event_type.value
    return event_type


class EventBus:
    """Simple event bus for domain events"""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Subscribe a handler to an event type.

        Args:
            event_type: Event type (e.g., 'time_entry.created')
            handler: Function to call when event is emitted
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe a handler from an event type"""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Emit an event to all subscribed handlers.

        Args:
            event_type: Event type
            data: Event data
        """
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event_type, data)
            except Exception as e:
                current_app.logger.error(f"Error in event handler for {event_type}: {e}", exc_info=True)

    def clear(self) -> None:
        """Clear all event handlers"""
        self._handlers.clear()


# Global event bus instance
_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    return _event_bus


def emit_event(event_type: EventType, data: Dict[str, Any]) -> None:
    """
    Emit an event using the global event bus.

    Args:
        event_type: Event type (``str`` or ``WebhookEvent``)
        data: Event data
    """
    _event_bus.emit(_coerce_event_type(event_type), data)


def subscribe_to_event(event_type: str):
    """
    Decorator to subscribe a function to an event type.

    Usage:
        @subscribe_to_event('time_entry.created')
        def handle_time_entry_created(event_type, data):
            # Handle event
    """

    def decorator(func: Callable) -> Callable:
        _event_bus.subscribe(event_type, func)
        return func

    return decorator


# Example event handlers
@subscribe_to_event(WebhookEvent.TIME_ENTRY_CREATED.value)
def handle_time_entry_created(event_type: str, data: Dict[str, Any]) -> None:
    """Handle time entry created event"""
    try:
        from app.utils.webhook_dispatcher import dispatch_webhook

        dispatch_webhook(event_type, data)
    except Exception as e:
        current_app.logger.error(f"Failed to dispatch webhook for {event_type}: {e}")


@subscribe_to_event(WebhookEvent.PROJECT_CREATED.value)
def handle_project_created(event_type: str, data: Dict[str, Any]) -> None:
    """Handle project created event"""
    try:
        from app.utils.webhook_dispatcher import dispatch_webhook

        dispatch_webhook(event_type, data)
    except Exception as e:
        current_app.logger.error(f"Failed to dispatch webhook for {event_type}: {e}")


@subscribe_to_event(WebhookEvent.INVOICE_CREATED.value)
def handle_invoice_created(event_type: str, data: Dict[str, Any]) -> None:
    """Handle invoice created event"""
    try:
        from app.utils.webhook_dispatcher import dispatch_webhook

        dispatch_webhook(event_type, data)
    except Exception as e:
        current_app.logger.error(f"Failed to dispatch webhook for {event_type}: {e}")

    try:
        from app.utils.workflow_bridge import handle_domain_event_for_workflows

        handle_domain_event_for_workflows(event_type, data)
    except Exception as e:
        current_app.logger.error(f"Failed to trigger workflows for {event_type}: {e}")


def _workflow_bridge_handler(event_type: str, data: Dict[str, Any]) -> None:
    try:
        from app.utils.workflow_bridge import handle_domain_event_for_workflows

        handle_domain_event_for_workflows(event_type, data)
    except Exception as e:
        current_app.logger.error(f"Failed to trigger workflows for {event_type}: {e}")


# Register workflow bridge for mapped webhook events (not time_entry.created — time_logged fires on stop/manual)
for _evt in (
    WebhookEvent.TASK_CREATED.value,
    WebhookEvent.INVOICE_PAID.value,
):
    _event_bus.subscribe(_evt, _workflow_bridge_handler)
