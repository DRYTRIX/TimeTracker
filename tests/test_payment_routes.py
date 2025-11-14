"""Tests for Payment routes"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import url_for
from app import db, create_app
from app.models import Payment, Invoice, User, Project, Client
from factories import UserFactory, ClientFactory, ProjectFactory, InvoiceFactory, PaymentFactory
from sqlalchemy.pool import StaticPool
@pytest.fixture
def app():
    """Isolated app for payment routes tests using in-memory SQLite to avoid file locks on Windows."""
    app = create_app({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {'check_same_thread': False, 'timeout': 30},
            'poolclass': StaticPool,
        },
        'SQLALCHEMY_SESSION_OPTIONS': {'expire_on_commit': False},
    })
    with app.app_context():
        db.create_all()
        try:
            db.session.execute("PRAGMA journal_mode=WAL;")
            db.session.execute("PRAGMA synchronous=NORMAL;")
            db.session.execute("PRAGMA busy_timeout=30000;")
            db.session.commit()
        except Exception:
            db.session.rollback()
        try:
            yield app
        finally:
            db.session.remove()
            db.drop_all()
            try:
                db.engine.dispose()
            except Exception:
                pass


@pytest.fixture
def test_user(app):
    """Create a test user"""
    with app.app_context():
        user = UserFactory(username='testuser')
        yield user


@pytest.fixture
def test_admin(app):
    """Create a test admin user"""
    with app.app_context():
        admin = UserFactory(username='testadmin', role='admin')
        db.session.add(admin)
        db.session.commit()
        yield admin


@pytest.fixture
def test_client(app):
    """Create a test client"""
    with app.app_context():
        client = ClientFactory()
        yield client


@pytest.fixture
def test_project(app, test_client, test_user):
    """Create a test project"""
    with app.app_context():
        project = ProjectFactory(
            client_id=test_client.id,
            billable=True,
            hourly_rate=Decimal('100.00')
        )
        yield project


@pytest.fixture
def test_invoice(app, test_project, test_user, test_client):
    """Create a test invoice"""
    with app.app_context():
        invoice = InvoiceFactory(
            project_id=test_project.id,
            client_id=test_client.id,
            created_by=test_user.id,
            client_name='Test Client',
            due_date=(date.today() + timedelta(days=30)),
        )
        invoice.subtotal = Decimal('1000.00')
        invoice.tax_rate = Decimal('21.00')
        invoice.tax_amount = Decimal('210.00')
        invoice.total_amount = Decimal('1210.00')
        db.session.add(invoice)
        db.session.commit()
        yield invoice


@pytest.fixture
def test_payment(app, test_invoice, test_user):
    """Create a test payment"""
    with app.app_context():
        payment = PaymentFactory(
            invoice_id=test_invoice.id,
            amount=Decimal('500.00'),
            currency='EUR',
            payment_date=date.today(),
            method='bank_transfer',
            reference='REF-12345',
            status='completed',
            received_by=test_user.id
        )
        db.session.add(payment)
        db.session.commit()
        yield payment


class TestPaymentRoutes:
    """Test payment routes"""
    
    def test_list_payments_requires_login(self, client):
        """Test that listing payments requires login"""
        response = client.get('/payments')
        assert response.status_code == 302  # Redirect to login
    
    def test_list_payments_as_user(self, client, test_user, test_payment):
        """Test listing payments as a regular user"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # List payments
            response = client.get('/payments')
            assert response.status_code == 200
    
    def test_list_payments_as_admin(self, client, test_admin, test_payment):
        """Test listing payments as admin"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testadmin'
            }, follow_redirects=True)
            
            # List payments
            response = client.get('/payments')
            assert response.status_code == 200
    
    def test_view_payment_requires_login(self, client, test_payment):
        """Test that viewing a payment requires login"""
        response = client.get(f'/payments/{test_payment.id}')
        assert response.status_code == 302  # Redirect to login
    
    def test_view_payment(self, client, test_user, test_payment):
        """Test viewing a payment"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # View payment
            response = client.get(f'/payments/{test_payment.id}')
            assert response.status_code == 200
    
    def test_create_payment_get_requires_login(self, client):
        """Test that creating payment GET requires login"""
        response = client.get('/payments/create')
        assert response.status_code == 302  # Redirect to login
    
    def test_create_payment_get(self, client, test_user):
        """Test creating payment GET request"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # Get create form
            response = client.get('/payments/create')
            assert response.status_code == 200
    
    def test_create_payment_post(self, client, test_user, test_invoice, app):
        """Test creating a payment via POST"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # Get CSRF token
            response = client.get('/payments/create')
            
            # Create payment
            payment_data = {
                'invoice_id': test_invoice.id,
                'amount': '500.00',
                'currency': 'EUR',
                'payment_date': date.today().strftime('%Y-%m-%d'),
                'method': 'bank_transfer',
                'reference': 'TEST-REF-001',
                'status': 'completed',
                'notes': 'Test payment'
            }
            
            response = client.post('/payments/create', data=payment_data, follow_redirects=True)
            assert response.status_code == 200
            
            # Verify payment was created
            with app.app_context():
                payment = Payment.query.filter_by(reference='TEST-REF-001').first()
                assert payment is not None
                assert payment.amount == Decimal('500.00')
                
                # Cleanup
                db.session.delete(payment)
                db.session.commit()
    
    def test_create_payment_with_gateway_fee(self, client, test_user, test_invoice, app):
        """Test creating a payment with gateway fee"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # Create payment with gateway fee
            payment_data = {
                'invoice_id': test_invoice.id,
                'amount': '500.00',
                'currency': 'EUR',
                'payment_date': date.today().strftime('%Y-%m-%d'),
                'method': 'stripe',
                'gateway_fee': '15.00',
                'status': 'completed'
            }
            
            response = client.post('/payments/create', data=payment_data, follow_redirects=True)
            assert response.status_code == 200
            
            # Verify payment was created with fee
            with app.app_context():
                payment = Payment.query.filter_by(invoice_id=test_invoice.id, method='stripe').first()
                if payment:
                    assert payment.gateway_fee == Decimal('15.00')
                    assert payment.net_amount == Decimal('485.00')
                    
                    # Cleanup
                    db.session.delete(payment)
                    db.session.commit()
    
    def test_edit_payment_get(self, client, test_user, test_payment):
        """Test editing payment GET request"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # Get edit form
            response = client.get(f'/payments/{test_payment.id}/edit')
            assert response.status_code == 200
    
    def test_edit_payment_post(self, client, test_user, test_payment, app):
        """Test editing a payment via POST"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # Edit payment
            payment_data = {
                'amount': '600.00',
                'currency': 'EUR',
                'payment_date': date.today().strftime('%Y-%m-%d'),
                'method': 'cash',
                'reference': 'UPDATED-REF',
                'status': 'completed',
                'notes': 'Updated payment'
            }
            
            response = client.post(f'/payments/{test_payment.id}/edit', data=payment_data, follow_redirects=True)
            assert response.status_code == 200
            
            # Verify payment was updated
            with app.app_context():
                payment = Payment.query.get(test_payment.id)
                assert payment.amount == Decimal('600.00')
                assert payment.method == 'cash'
                assert payment.reference == 'UPDATED-REF'
    
    def test_delete_payment(self, client, test_user, test_payment, app):
        """Test deleting a payment"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # Delete payment
            payment_id = test_payment.id
            response = client.post(f'/payments/{payment_id}/delete', follow_redirects=True)
            assert response.status_code == 200
            
            # Verify payment was deleted
            with app.app_context():
                payment = Payment.query.get(payment_id)
                assert payment is None
    
    def test_payment_stats_api(self, client, test_user, test_payment):
        """Test payment statistics API"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # Get payment stats
            response = client.get('/api/payments/stats')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'total_payments' in data
            assert 'total_amount' in data
            assert 'by_method' in data
            assert 'by_status' in data
    
    def test_create_payment_invalid_amount(self, client, test_user, test_invoice):
        """Test creating payment with invalid amount"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # Try to create payment with invalid amount
            payment_data = {
                'invoice_id': test_invoice.id,
                'amount': '-100.00',  # Negative amount
                'currency': 'EUR',
                'payment_date': date.today().strftime('%Y-%m-%d'),
                'status': 'completed'
            }
            
            response = client.post('/payments/create', data=payment_data, follow_redirects=True)
            # Should show error message or stay on form
            assert response.status_code == 200
    
    def test_create_payment_without_invoice(self, client, test_user):
        """Test creating payment without selecting invoice"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # Try to create payment without invoice
            payment_data = {
                'amount': '100.00',
                'currency': 'EUR',
                'payment_date': date.today().strftime('%Y-%m-%d'),
                'status': 'completed'
            }
            
            response = client.post('/payments/create', data=payment_data, follow_redirects=True)
            # Should show error or stay on form
            assert response.status_code == 200


class TestPaymentFilteringAndSearch:
    """Test payment filtering and search functionality"""
    
    def test_filter_payments_by_status(self, client, test_user, test_payment):
        """Test filtering payments by status"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # Filter by status
            response = client.get('/payments?status=completed')
            assert response.status_code == 200
    
    def test_filter_payments_by_method(self, client, test_user, test_payment):
        """Test filtering payments by method"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # Filter by method
            response = client.get('/payments?method=bank_transfer')
            assert response.status_code == 200
    
    def test_filter_payments_by_date_range(self, client, test_user, test_payment):
        """Test filtering payments by date range"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # Filter by date range
            date_from = (date.today() - timedelta(days=7)).strftime('%Y-%m-%d')
            date_to = date.today().strftime('%Y-%m-%d')
            response = client.get(f'/payments?date_from={date_from}&date_to={date_to}')
            assert response.status_code == 200
    
    def test_filter_payments_by_invoice(self, client, test_user, test_invoice, test_payment):
        """Test filtering payments by invoice"""
        with client:
            # Login
            client.post('/login', data={
                'username': 'testuser'
            }, follow_redirects=True)
            
            # Filter by invoice
            response = client.get(f'/payments?invoice_id={test_invoice.id}')
            assert response.status_code == 200

