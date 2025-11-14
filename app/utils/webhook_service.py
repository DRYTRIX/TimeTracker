"""Webhook delivery service for sending events to external systems"""
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import requests
from flask import current_app
from app import db
from app.models.webhook import Webhook, WebhookDelivery
from app.utils.timezone import now_in_app_timezone

logger = logging.getLogger(__name__)


class WebhookDeliveryError(Exception):
    """Base exception for webhook delivery errors"""
    pass


class WebhookTimeoutError(WebhookDeliveryError):
    """Raised when webhook delivery times out"""
    pass


class WebhookHTTPError(WebhookDeliveryError):
    """Raised when webhook delivery returns HTTP error"""
    pass


class WebhookService:
    """Service for delivering webhooks to external systems"""
    
    @staticmethod
    def deliver_webhook(webhook: Webhook, event_type: str, payload: Dict[str, Any], 
                       event_id: Optional[str] = None) -> WebhookDelivery:
        """Deliver a webhook event to the configured URL
        
        Args:
            webhook: Webhook configuration
            event_type: Event type (e.g., 'project.created')
            payload: Event payload dictionary
            event_id: Optional unique event ID for deduplication
            
        Returns:
            WebhookDelivery: Delivery record
        """
        if not webhook.is_active:
            raise WebhookDeliveryError(f"Webhook {webhook.id} is not active")
        
        if not webhook.subscribes_to(event_type):
            raise WebhookDeliveryError(f"Webhook {webhook.id} does not subscribe to event {event_type}")
        
        # Generate event ID if not provided
        if not event_id:
            event_id = str(uuid.uuid4())
        
        # Serialize payload
        payload_json = json.dumps(payload, default=str)
        payload_hash = WebhookDelivery.hash_payload(payload_json)
        
        # Create delivery record
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type=event_type,
            event_id=event_id,
            payload=payload_json,
            payload_hash=payload_hash,
            status='pending',
            attempt_number=1
        )
        db.session.add(delivery)
        
        try:
            # Attempt delivery
            start_time = time.time()
            delivery.started_at = now_in_app_timezone()
            
            response = WebhookService._send_request(webhook, payload_json, event_type)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Check response status
            if 200 <= response.status_code < 300:
                # Success
                delivery.mark_success(
                    status_code=response.status_code,
                    response_body=response.text[:10000],  # Limit response body size
                    response_headers=dict(response.headers),
                    duration_ms=duration_ms
                )
                logger.info(f"Webhook {webhook.id} delivered successfully: {event_type}")
            else:
                # HTTP error
                delivery.mark_failed(
                    error_message=f"HTTP {response.status_code}: {response.text[:500]}",
                    error_type='http_error',
                    response_status_code=response.status_code,
                    response_body=response.text[:10000],
                    duration_ms=duration_ms
                )
                logger.warning(f"Webhook {webhook.id} failed with HTTP {response.status_code}: {event_type}")
                
                # Schedule retry if not exceeded max retries
                WebhookService._schedule_retry(delivery, webhook)
            
        except requests.exceptions.Timeout as e:
            duration_ms = int((time.time() - start_time) * 1000)
            delivery.mark_failed(
                error_message=f"Request timeout after {webhook.timeout_seconds}s",
                error_type='timeout',
                duration_ms=duration_ms
            )
            logger.warning(f"Webhook {webhook.id} timed out: {event_type}")
            WebhookService._schedule_retry(delivery, webhook)
            
        except requests.exceptions.ConnectionError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            delivery.mark_failed(
                error_message=f"Connection error: {str(e)[:500]}",
                error_type='connection_error',
                duration_ms=duration_ms
            )
            logger.warning(f"Webhook {webhook.id} connection error: {event_type}")
            WebhookService._schedule_retry(delivery, webhook)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            delivery.mark_failed(
                error_message=f"Unexpected error: {str(e)[:500]}",
                error_type='unknown_error',
                duration_ms=duration_ms
            )
            logger.error(f"Webhook {webhook.id} unexpected error: {event_type}", exc_info=True)
            WebhookService._schedule_retry(delivery, webhook)
        
        finally:
            db.session.commit()
        
        return delivery
    
    @staticmethod
    def _send_request(webhook: Webhook, payload_json: str, event_type: str) -> requests.Response:
        """Send HTTP request to webhook URL
        
        Args:
            webhook: Webhook configuration
            payload_json: JSON-encoded payload
            event_type: Event type
            
        Returns:
            requests.Response: HTTP response
        """
        # Prepare headers
        headers = {
            'Content-Type': webhook.content_type,
            'User-Agent': 'TimeTracker-Webhook/1.0',
            'X-Webhook-Event': event_type,
            'X-Webhook-ID': str(webhook.id),
        }
        
        # Add custom headers
        if webhook.headers:
            headers.update(webhook.headers)
        
        # Add signature if secret is configured
        if webhook.secret:
            signature = webhook.generate_signature(payload_json)
            headers['X-Webhook-Signature'] = signature
        
        # Prepare request kwargs
        request_kwargs = {
            'url': webhook.url,
            'headers': headers,
            'data': payload_json if webhook.content_type == 'application/json' else payload_json,
            'timeout': webhook.timeout_seconds,
            'allow_redirects': True,
        }
        
        # Send request based on HTTP method
        if webhook.http_method.upper() == 'POST':
            response = requests.post(**request_kwargs)
        elif webhook.http_method.upper() == 'PUT':
            response = requests.put(**request_kwargs)
        elif webhook.http_method.upper() == 'PATCH':
            response = requests.patch(**request_kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {webhook.http_method}")
        
        return response
    
    @staticmethod
    def _schedule_retry(delivery: WebhookDelivery, webhook: Webhook):
        """Schedule a retry for failed delivery
        
        Args:
            delivery: Failed delivery record
            webhook: Webhook configuration
        """
        if delivery.retry_count >= webhook.max_retries:
            logger.info(f"Webhook {webhook.id} delivery {delivery.id} exceeded max retries")
            return
        
        # Calculate next retry time with exponential backoff
        delay_seconds = webhook.retry_delay_seconds * (2 ** delivery.retry_count)
        next_retry_at = now_in_app_timezone() + timedelta(seconds=delay_seconds)
        
        delivery.mark_retrying(next_retry_at)
        logger.info(f"Scheduled retry for webhook {webhook.id} delivery {delivery.id} at {next_retry_at}")
    
    @staticmethod
    def retry_failed_deliveries(max_deliveries: int = 100) -> int:
        """Retry failed webhook deliveries that are scheduled for retry
        
        Args:
            max_deliveries: Maximum number of deliveries to process in this run
            
        Returns:
            int: Number of deliveries retried
        """
        now = now_in_app_timezone()
        
        # Find deliveries ready for retry
        deliveries = WebhookDelivery.query.filter(
            WebhookDelivery.status == 'retrying',
            WebhookDelivery.next_retry_at <= now
        ).limit(max_deliveries).all()
        
        retried_count = 0
        
        for delivery in deliveries:
            webhook = delivery.webhook
            
            if not webhook or not webhook.is_active:
                # Mark as failed if webhook is deleted or inactive
                delivery.mark_failed(
                    error_message="Webhook is inactive or deleted",
                    error_type='webhook_inactive'
                )
                db.session.commit()
                continue
            
            try:
                # Retry delivery
                start_time = time.time()
                delivery.started_at = now_in_app_timezone()
                delivery.attempt_number += 1
                
                response = WebhookService._send_request(webhook, delivery.payload, delivery.event_type)
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                if 200 <= response.status_code < 300:
                    delivery.mark_success(
                        status_code=response.status_code,
                        response_body=response.text[:10000],
                        response_headers=dict(response.headers),
                        duration_ms=duration_ms
                    )
                    logger.info(f"Webhook {webhook.id} retry successful: {delivery.event_type}")
                else:
                    delivery.mark_failed(
                        error_message=f"HTTP {response.status_code}: {response.text[:500]}",
                        error_type='http_error',
                        response_status_code=response.status_code,
                        response_body=response.text[:10000],
                        duration_ms=duration_ms
                    )
                    WebhookService._schedule_retry(delivery, webhook)
                
                retried_count += 1
                
            except requests.exceptions.Timeout as e:
                duration_ms = int((time.time() - start_time) * 1000)
                delivery.mark_failed(
                    error_message=f"Request timeout after {webhook.timeout_seconds}s",
                    error_type='timeout',
                    duration_ms=duration_ms
                )
                WebhookService._schedule_retry(delivery, webhook)
                retried_count += 1
                
            except requests.exceptions.ConnectionError as e:
                duration_ms = int((time.time() - start_time) * 1000)
                delivery.mark_failed(
                    error_message=f"Connection error: {str(e)[:500]}",
                    error_type='connection_error',
                    duration_ms=duration_ms
                )
                WebhookService._schedule_retry(delivery, webhook)
                retried_count += 1
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                delivery.mark_failed(
                    error_message=f"Unexpected error: {str(e)[:500]}",
                    error_type='unknown_error',
                    duration_ms=duration_ms
                )
                WebhookService._schedule_retry(delivery, webhook)
                retried_count += 1
                logger.error(f"Error retrying webhook {webhook.id} delivery {delivery.id}", exc_info=True)
            
            finally:
                db.session.commit()
        
        return retried_count
    
    @staticmethod
    def get_available_events() -> List[str]:
        """Get list of available webhook event types
        
        Returns:
            List[str]: List of event type strings
        """
        return [
            # Project events
            'project.created',
            'project.updated',
            'project.deleted',
            'project.archived',
            'project.unarchived',
            
            # Task events
            'task.created',
            'task.updated',
            'task.deleted',
            'task.completed',
            'task.assigned',
            'task.status_changed',
            
            # Time entry events
            'time_entry.created',
            'time_entry.updated',
            'time_entry.deleted',
            'time_entry.started',
            'time_entry.stopped',
            
            # Invoice events
            'invoice.created',
            'invoice.updated',
            'invoice.deleted',
            'invoice.sent',
            'invoice.paid',
            'invoice.overdue',
            
            # Client events
            'client.created',
            'client.updated',
            'client.deleted',
            
            # User events
            'user.created',
            'user.updated',
            'user.deleted',
            
            # Comment events
            'comment.created',
            'comment.updated',
            'comment.deleted',
        ]

