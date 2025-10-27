"""Tests for Payment model"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.models import Payment, Invoice, User, Project, Client


@pytest.fixture
def test_user(app):
    """Create a test user"""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.role = 'user'
        db.session.add(user)
        db.session.commit()
        yield user
        # Cleanup
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def test_client(app):
    """Create a test client"""
    with app.app_context():
        client = Client(name='Test Client', email='client@example.com')
        db.session.add(client)
        db.session.commit()
        yield client
        # Cleanup
        db.session.delete(client)
        db.session.commit()


@pytest.fixture
def test_project(app, test_client, test_user):
    """Create a test project"""
    with app.app_context():
        project = Project(
            name='Test Project',
            client_id=test_client.id,
            created_by=test_user.id,
            billable=True,
            hourly_rate=Decimal('100.00')
        )
        db.session.add(project)
        db.session.commit()
        yield project
        # Cleanup
        db.session.delete(project)
        db.session.commit()


@pytest.fixture
def test_invoice(app, test_project, test_user, test_client):
    """Create a test invoice"""
    with app.app_context():
        invoice = Invoice(
            invoice_number='INV-TEST-001',
            project_id=test_project.id,
            client_name='Test Client',
            client_id=test_client.id,
            due_date=date.today() + timedelta(days=30),
            created_by=test_user.id
        )
        invoice.subtotal = Decimal('1000.00')
        invoice.tax_rate = Decimal('21.00')
        invoice.tax_amount = Decimal('210.00')
        invoice.total_amount = Decimal('1210.00')
        db.session.add(invoice)
        db.session.commit()
        yield invoice
        # Cleanup
        db.session.delete(invoice)
        db.session.commit()


class TestPaymentModel:
    """Test Payment model functionality"""
    
    def test_create_payment(self, app, test_invoice, test_user):
        """Test creating a payment"""
        with app.app_context():
            payment = Payment(
                invoice_id=test_invoice.id,
                amount=Decimal('500.00'),
                currency='EUR',
                payment_date=date.today(),
                method='bank_transfer',
                reference='REF-12345',
                notes='Test payment',
                status='completed',
                received_by=test_user.id
            )
            
            db.session.add(payment)
            db.session.commit()
            
            # Verify payment was created
            assert payment.id is not None
            assert payment.amount == Decimal('500.00')
            assert payment.currency == 'EUR'
            assert payment.method == 'bank_transfer'
            assert payment.status == 'completed'
            
            # Cleanup
            db.session.delete(payment)
            db.session.commit()
    
    def test_payment_calculate_net_amount_without_fee(self, app, test_invoice):
        """Test calculating net amount without gateway fee"""
        with app.app_context():
            payment = Payment(
                invoice_id=test_invoice.id,
                amount=Decimal('500.00'),
                currency='EUR',
                payment_date=date.today(),
                status='completed'
            )
            
            payment.calculate_net_amount()
            
            assert payment.net_amount == Decimal('500.00')
            
            # Cleanup (not in DB yet, so no cleanup needed)
    
    def test_payment_calculate_net_amount_with_fee(self, app, test_invoice):
        """Test calculating net amount with gateway fee"""
        with app.app_context():
            payment = Payment(
                invoice_id=test_invoice.id,
                amount=Decimal('500.00'),
                currency='EUR',
                payment_date=date.today(),
                gateway_fee=Decimal('15.00'),
                status='completed'
            )
            
            payment.calculate_net_amount()
            
            assert payment.net_amount == Decimal('485.00')
    
    def test_payment_to_dict(self, app, test_invoice, test_user):
        """Test converting payment to dictionary"""
        with app.app_context():
            payment = Payment(
                invoice_id=test_invoice.id,
                amount=Decimal('500.00'),
                currency='EUR',
                payment_date=date.today(),
                method='bank_transfer',
                reference='REF-12345',
                notes='Test payment',
                status='completed',
                received_by=test_user.id,
                gateway_fee=Decimal('15.00'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            payment.calculate_net_amount()
            
            db.session.add(payment)
            db.session.commit()
            
            payment_dict = payment.to_dict()
            
            assert payment_dict['invoice_id'] == test_invoice.id
            assert payment_dict['amount'] == 500.0
            assert payment_dict['currency'] == 'EUR'
            assert payment_dict['method'] == 'bank_transfer'
            assert payment_dict['reference'] == 'REF-12345'
            assert payment_dict['status'] == 'completed'
            assert payment_dict['gateway_fee'] == 15.0
            assert payment_dict['net_amount'] == 485.0
            
            # Cleanup
            db.session.delete(payment)
            db.session.commit()
    
    def test_payment_relationship_with_invoice(self, app, test_invoice):
        """Test payment relationship with invoice"""
        with app.app_context():
            # Re-query invoice to attach to current session
            from app.models.invoice import Invoice
            invoice_in_session = Invoice.query.get(test_invoice.id)
            
            payment = Payment(
                invoice_id=invoice_in_session.id,
                amount=Decimal('500.00'),
                currency='EUR',
                payment_date=date.today(),
                status='completed'
            )
            
            db.session.add(payment)
            db.session.commit()
            
            # Refresh invoice to get updated relationships
            db.session.refresh(invoice_in_session)
            
            # Verify relationship
            assert payment.invoice == invoice_in_session
            assert payment in invoice_in_session.payments
            
            # Cleanup
            db.session.delete(payment)
            db.session.commit()
    
    def test_payment_relationship_with_user(self, app, test_invoice, test_user):
        """Test payment relationship with user (receiver)"""
        with app.app_context():
            # Re-query user to attach to current session
            from app.models.user import User
            user_in_session = User.query.get(test_user.id)
            
            payment = Payment(
                invoice_id=test_invoice.id,
                amount=Decimal('500.00'),
                currency='EUR',
                payment_date=date.today(),
                status='completed',
                received_by=user_in_session.id
            )
            
            db.session.add(payment)
            db.session.commit()
            
            # Refresh user to get updated relationships
            db.session.refresh(user_in_session)
            
            # Verify relationship
            assert payment.receiver == user_in_session
            assert payment in user_in_session.received_payments
            
            # Cleanup
            db.session.delete(payment)
            db.session.commit()
    
    def test_payment_repr(self, app, test_invoice):
        """Test payment string representation"""
        with app.app_context():
            payment = Payment(
                invoice_id=test_invoice.id,
                amount=Decimal('500.00'),
                currency='EUR',
                payment_date=date.today(),
                status='completed'
            )
            
            repr_str = repr(payment)
            assert 'Payment' in repr_str
            assert '500.00' in repr_str
            assert 'EUR' in repr_str
    
    def test_multiple_payments_for_invoice(self, app, test_invoice):
        """Test multiple payments for a single invoice"""
        with app.app_context():
            # Re-query invoice to attach to current session
            from app.models.invoice import Invoice
            invoice_in_session = Invoice.query.get(test_invoice.id)
            
            payment1 = Payment(
                invoice_id=invoice_in_session.id,
                amount=Decimal('300.00'),
                currency='EUR',
                payment_date=date.today(),
                status='completed'
            )
            
            payment2 = Payment(
                invoice_id=invoice_in_session.id,
                amount=Decimal('200.00'),
                currency='EUR',
                payment_date=date.today() + timedelta(days=1),
                status='completed'
            )
            
            db.session.add_all([payment1, payment2])
            db.session.commit()
            
            # Refresh invoice to get updated relationships
            db.session.refresh(invoice_in_session)
            
            # Verify both payments are associated with invoice
            assert invoice_in_session.payments.count() == 2
            
            # Cleanup
            db.session.delete(payment1)
            db.session.delete(payment2)
            db.session.commit()
    
    def test_payment_status_values(self, app, test_invoice):
        """Test different payment status values"""
        with app.app_context():
            statuses = ['completed', 'pending', 'failed', 'refunded']
            
            for status in statuses:
                payment = Payment(
                    invoice_id=test_invoice.id,
                    amount=Decimal('100.00'),
                    currency='EUR',
                    payment_date=date.today(),
                    status=status
                )
                
                db.session.add(payment)
                db.session.commit()
                
                assert payment.status == status
                
                # Cleanup
                db.session.delete(payment)
                db.session.commit()


class TestPaymentIntegration:
    """Test Payment model integration with Invoice"""
    
    def test_invoice_updates_with_payment(self, app, test_invoice):
        """Test that invoice updates correctly when payment is added"""
        with app.app_context():
            # Initial state
            assert test_invoice.amount_paid == Decimal('0')
            assert test_invoice.payment_status == 'unpaid'
            
            # Add payment
            payment = Payment(
                invoice_id=test_invoice.id,
                amount=Decimal('605.00'),  # Half of total
                currency='EUR',
                payment_date=date.today(),
                status='completed'
            )
            
            db.session.add(payment)
            
            # Update invoice manually (this would be done by route logic)
            test_invoice.amount_paid = (test_invoice.amount_paid or Decimal('0')) + payment.amount
            test_invoice.update_payment_status()
            
            db.session.commit()
            
            # Verify invoice was updated
            assert test_invoice.amount_paid == Decimal('605.00')
            assert test_invoice.payment_status == 'partially_paid'
            
            # Cleanup
            db.session.delete(payment)
            test_invoice.amount_paid = Decimal('0')
            test_invoice.update_payment_status()
            db.session.commit()
    
    def test_invoice_fully_paid_with_payments(self, app, test_invoice):
        """Test that invoice becomes fully paid when total payments equal total amount"""
        with app.app_context():
            # Add payments that equal total amount
            payment = Payment(
                invoice_id=test_invoice.id,
                amount=test_invoice.total_amount,
                currency='EUR',
                payment_date=date.today(),
                status='completed'
            )
            
            db.session.add(payment)
            
            # Update invoice manually (this would be done by route logic)
            test_invoice.amount_paid = payment.amount
            test_invoice.update_payment_status()
            
            db.session.commit()
            
            # Verify invoice is fully paid
            assert test_invoice.payment_status == 'fully_paid'
            assert test_invoice.is_paid is True
            
            # Cleanup
            db.session.delete(payment)
            test_invoice.amount_paid = Decimal('0')
            test_invoice.update_payment_status()
            db.session.commit()

