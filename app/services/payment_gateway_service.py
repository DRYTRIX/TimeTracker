"""
Service for payment gateway business logic.
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
from app import db
from app.models import PaymentGateway, PaymentTransaction, Invoice
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent
from app.utils.timezone import now_in_app_timezone
import logging

logger = logging.getLogger(__name__)


class PaymentGatewayService:
    """
    Service for payment gateway operations.
    """
    
    def create_gateway(
        self,
        name: str,
        provider: str,
        config: Dict[str, Any],
        is_test_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Create a payment gateway configuration.
        
        Args:
            name: Gateway name (e.g., 'stripe_production')
            provider: Provider type ('stripe', 'paypal', 'square')
            config: Configuration dict (will be encrypted)
            is_test_mode: Whether in test mode
        
        Returns:
            dict with 'success', 'message', and 'gateway' keys
        """
        try:
            # Check if name already exists
            existing = PaymentGateway.query.filter_by(name=name).first()
            if existing:
                return {
                    'success': False,
                    'message': 'A gateway with this name already exists.'
                }
            
            # Encrypt config (in production, use proper encryption)
            # For now, we'll store as JSON string
            import json
            config_json = json.dumps(config)
            
            gateway = PaymentGateway(
                name=name,
                provider=provider,
                config=config_json,
                is_active=True,
                is_test_mode=is_test_mode
            )
            
            db.session.add(gateway)
            if not safe_commit('create_gateway', {'name': name}):
                return {
                    'success': False,
                    'message': 'Could not create gateway due to a database error.'
                }
            
            return {
                'success': True,
                'message': 'Payment gateway created successfully.',
                'gateway': gateway
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating payment gateway: {e}")
            return {
                'success': False,
                'message': f'Error creating gateway: {str(e)}'
            }
    
    def get_gateway(self, gateway_id: int) -> Optional[PaymentGateway]:
        """Get a gateway by ID"""
        return PaymentGateway.query.get(gateway_id)
    
    def get_active_gateway(self, provider: Optional[str] = None) -> Optional[PaymentGateway]:
        """Get the active gateway for a provider"""
        query = PaymentGateway.query.filter_by(is_active=True)
        if provider:
            query = query.filter_by(provider=provider)
        return query.first()
    
    def process_payment(
        self,
        invoice_id: int,
        gateway_id: int,
        amount: Decimal,
        payment_method: str,
        gateway_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a payment through a gateway.
        
        Returns:
            dict with 'success', 'message', and 'transaction' keys
        """
        try:
            invoice = Invoice.query.get(invoice_id)
            if not invoice:
                return {
                    'success': False,
                    'message': 'Invoice not found.'
                }
            
            gateway = PaymentGateway.query.get(gateway_id)
            if not gateway or not gateway.is_active:
                return {
                    'success': False,
                    'message': 'Payment gateway not found or inactive.'
                }
            
            # Generate transaction ID (will be replaced by gateway response)
            transaction_id = f"{gateway.provider}_{invoice_id}_{int(now_in_app_timezone().timestamp())}"
            
            # Create transaction record
            transaction = PaymentTransaction(
                invoice_id=invoice_id,
                gateway_id=gateway_id,
                transaction_id=transaction_id,
                amount=amount,
                currency=invoice.currency_code,
                status='processing',
                payment_method=payment_method,
                gateway_response=gateway_response
            )
            
            db.session.add(transaction)
            
            # Update invoice payment status
            invoice.amount_paid = (invoice.amount_paid or Decimal('0')) + amount
            if invoice.amount_paid >= invoice.total_amount:
                invoice.payment_status = 'fully_paid'
                invoice.status = 'paid'
                invoice.payment_date = now_in_app_timezone().date()
            elif invoice.amount_paid > Decimal('0'):
                invoice.payment_status = 'partially_paid'
            
            if not safe_commit('process_payment', {'invoice_id': invoice_id}):
                return {
                    'success': False,
                    'message': 'Could not process payment due to a database error.'
                }
            
            emit_event(WebhookEvent.PAYMENT_PROCESSED, {
                'invoice_id': invoice_id,
                'transaction_id': transaction.id,
                'amount': float(amount),
                'gateway': gateway.provider
            })
            
            return {
                'success': True,
                'message': 'Payment processed successfully.',
                'transaction': transaction
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing payment: {e}")
            return {
                'success': False,
                'message': f'Error processing payment: {str(e)}'
            }
    
    def update_transaction_status(
        self,
        transaction_id: str,
        status: str,
        gateway_response: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a payment transaction status (typically from webhook).
        
        Returns:
            dict with 'success', 'message', and 'transaction' keys
        """
        try:
            transaction = PaymentTransaction.query.filter_by(
                transaction_id=transaction_id
            ).first()
            
            if not transaction:
                return {
                    'success': False,
                    'message': 'Transaction not found.'
                }
            
            old_status = transaction.status
            transaction.status = status
            transaction.processed_at = now_in_app_timezone()
            
            if gateway_response:
                transaction.gateway_response = gateway_response
                # Extract gateway fee and net amount if available
                if 'fee' in gateway_response:
                    transaction.gateway_fee = Decimal(str(gateway_response['fee']))
                if 'net_amount' in gateway_response:
                    transaction.net_amount = Decimal(str(gateway_response['net_amount']))
            
            if error_message:
                transaction.error_message = error_message
            if error_code:
                transaction.error_code = error_code
            
            # Update invoice if payment completed or failed
            if status == 'completed' and old_status != 'completed':
                invoice = Invoice.query.get(transaction.invoice_id)
                if invoice:
                    invoice.amount_paid = (invoice.amount_paid or Decimal('0')) + transaction.amount
                    if invoice.amount_paid >= invoice.total_amount:
                        invoice.payment_status = 'fully_paid'
                        invoice.status = 'paid'
                        invoice.payment_date = now_in_app_timezone().date()
            
            if not safe_commit('update_transaction_status', {'transaction_id': transaction_id}):
                return {
                    'success': False,
                    'message': 'Could not update transaction due to a database error.'
                }
            
            if status == 'completed':
                emit_event(WebhookEvent.PAYMENT_PROCESSED, {
                    'invoice_id': transaction.invoice_id,
                    'transaction_id': transaction.id,
                    'amount': float(transaction.amount)
                })
            elif status == 'failed':
                emit_event(WebhookEvent.PAYMENT_FAILED, {
                    'invoice_id': transaction.invoice_id,
                    'transaction_id': transaction.id,
                    'error': error_message
                })
            
            return {
                'success': True,
                'message': 'Transaction updated successfully.',
                'transaction': transaction
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating transaction: {e}")
            return {
                'success': False,
                'message': f'Error updating transaction: {str(e)}'
            }
    
    def get_transaction(self, transaction_id: int) -> Optional[PaymentTransaction]:
        """Get a transaction by ID"""
        return PaymentTransaction.query.get(transaction_id)
    
    def get_invoice_transactions(self, invoice_id: int) -> List[PaymentTransaction]:
        """Get all transactions for an invoice"""
        return PaymentTransaction.query.filter_by(invoice_id=invoice_id).all()

