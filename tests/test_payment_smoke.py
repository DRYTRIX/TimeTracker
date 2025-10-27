"""Smoke tests for Payment tracking feature"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from app import db
from app.models import Payment, Invoice, User, Project, Client


@pytest.fixture
def setup_payment_test_data(app):
    """Setup test data for payment smoke tests"""
    with app.app_context():
        # Create user
        user = User(username='smoketest_user', email='smoke@example.com')
        user.role = 'admin'
        db.session.add(user)
        
        # Create client
        client = Client(name='Smoke Test Client', email='smoke_client@example.com')
        db.session.add(client)
        db.session.flush()
        
        # Create project
        project = Project(
            name='Smoke Test Project',
            client_id=client.id,
            created_by=user.id,
            billable=True,
            hourly_rate=Decimal('100.00')
        )
        db.session.add(project)
        db.session.flush()
        
        # Create invoice
        invoice = Invoice(
            invoice_number='INV-SMOKE-001',
            project_id=project.id,
            client_name='Smoke Test Client',
            client_id=client.id,
            due_date=date.today() + timedelta(days=30),
            created_by=user.id
        )
        invoice.subtotal = Decimal('1000.00')
        invoice.tax_rate = Decimal('21.00')
        invoice.tax_amount = Decimal('210.00')
        invoice.total_amount = Decimal('1210.00')
        db.session.add(invoice)
        db.session.commit()
        
        yield {
            'user': user,
            'client': client,
            'project': project,
            'invoice': invoice
        }
        
        # Cleanup
        Payment.query.filter_by(invoice_id=invoice.id).delete()
        db.session.delete(invoice)
        db.session.delete(project)
        db.session.delete(client)
        db.session.delete(user)
        db.session.commit()


class TestPaymentSmokeTests:
    """Smoke tests to verify basic payment functionality"""
    
    def test_payment_model_exists(self):
        """Test that Payment model exists and is importable"""
        from app.models import Payment
        assert Payment is not None
    
    def test_payment_blueprint_registered(self, app):
        """Test that payments blueprint is registered"""
        with app.app_context():
            assert 'payments' in app.blueprints
    
    def test_payment_routes_exist(self, app):
        """Test that payment routes are registered"""
        with app.app_context():
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            assert '/payments' in rules
            assert any('/payments/<int:payment_id>' in rule for rule in rules)
            assert '/payments/create' in rules
    
    def test_payment_database_table_exists(self, app):
        """Test that payments table exists in database"""
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            assert 'payments' in tables
    
    def test_payment_model_columns(self, app):
        """Test that payment model has required columns"""
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('payments')]
            
            # Required columns
            required_columns = [
                'id', 'invoice_id', 'amount', 'currency', 'payment_date',
                'method', 'reference', 'notes', 'status', 'received_by',
                'gateway_transaction_id', 'gateway_fee', 'net_amount',
                'created_at', 'updated_at'
            ]
            
            for col in required_columns:
                assert col in columns, f"Column '{col}' not found in payments table"
    
    def test_create_and_retrieve_payment(self, app, setup_payment_test_data):
        """Test creating and retrieving a payment"""
        with app.app_context():
            invoice = setup_payment_test_data['invoice']
            user = setup_payment_test_data['user']
            
            # Create payment
            payment = Payment(
                invoice_id=invoice.id,
                amount=Decimal('500.00'),
                currency='EUR',
                payment_date=date.today(),
                method='bank_transfer',
                status='completed',
                received_by=user.id
            )
            
            db.session.add(payment)
            db.session.commit()
            payment_id = payment.id
            
            # Retrieve payment
            retrieved_payment = Payment.query.get(payment_id)
            assert retrieved_payment is not None
            assert retrieved_payment.amount == Decimal('500.00')
            assert retrieved_payment.invoice_id == invoice.id
            
            # Cleanup
            db.session.delete(payment)
            db.session.commit()
    
    def test_payment_invoice_relationship(self, app, setup_payment_test_data):
        """Test relationship between payment and invoice"""
        with app.app_context():
            invoice = setup_payment_test_data['invoice']
            
            # Create payment
            payment = Payment(
                invoice_id=invoice.id,
                amount=Decimal('500.00'),
                currency='EUR',
                payment_date=date.today(),
                status='completed'
            )
            
            db.session.add(payment)
            db.session.commit()
            
            # Test relationship
            assert payment.invoice is not None
            assert payment.invoice.id == invoice.id
            
            # Refresh invoice to get updated relationships
            db.session.refresh(invoice)
            assert payment in invoice.payments
            
            # Cleanup
            db.session.delete(payment)
            db.session.commit()
    
    def test_payment_list_page_loads(self, client, setup_payment_test_data):
        """Test that payment list page loads"""
        with client:
            user = setup_payment_test_data['user']
            
            # Login
            client.post('/login', data={'username': user.username}, follow_redirects=True)
            
            # Access payments list
            response = client.get('/payments')
            assert response.status_code == 200
    
    def test_payment_create_page_loads(self, client, setup_payment_test_data):
        """Test that payment create page loads"""
        with client:
            user = setup_payment_test_data['user']
            
            # Login
            client.post('/login', data={'username': user.username}, follow_redirects=True)
            
            # Access payment create page
            response = client.get('/payments/create')
            assert response.status_code == 200
    
    def test_payment_workflow_end_to_end(self, client, app, setup_payment_test_data):
        """Test complete payment workflow from creation to viewing"""
        with client:
            user = setup_payment_test_data['user']
            invoice = setup_payment_test_data['invoice']
            
            # Login
            client.post('/login', data={'username': user.username}, follow_redirects=True)
            
            # Create payment
            payment_data = {
                'invoice_id': invoice.id,
                'amount': '500.00',
                'currency': 'EUR',
                'payment_date': date.today().strftime('%Y-%m-%d'),
                'method': 'bank_transfer',
                'reference': 'SMOKE-TEST-001',
                'status': 'completed',
                'notes': 'Smoke test payment'
            }
            
            create_response = client.post('/payments/create', data=payment_data, follow_redirects=True)
            assert create_response.status_code == 200
            
            # Verify payment was created in database
            with app.app_context():
                payment = Payment.query.filter_by(reference='SMOKE-TEST-001').first()
                assert payment is not None
                payment_id = payment.id
                
                # View payment
                view_response = client.get(f'/payments/{payment_id}')
                assert view_response.status_code == 200
                
                # Cleanup
                db.session.delete(payment)
                db.session.commit()
    
    def test_payment_templates_exist(self, app):
        """Test that payment templates exist"""
        import os
        
        template_dir = os.path.join(app.root_path, 'templates', 'payments')
        assert os.path.exists(template_dir), "Payments template directory does not exist"
        
        required_templates = ['list.html', 'create.html', 'edit.html', 'view.html']
        for template in required_templates:
            template_path = os.path.join(template_dir, template)
            assert os.path.exists(template_path), f"Template {template} does not exist"
    
    def test_payment_model_methods(self, app, setup_payment_test_data):
        """Test that payment model has required methods"""
        with app.app_context():
            invoice = setup_payment_test_data['invoice']
            
            payment = Payment(
                invoice_id=invoice.id,
                amount=Decimal('500.00'),
                currency='EUR',
                payment_date=date.today(),
                gateway_fee=Decimal('15.00'),
                status='completed'
            )
            
            # Test calculate_net_amount method
            assert hasattr(payment, 'calculate_net_amount')
            payment.calculate_net_amount()
            assert payment.net_amount == Decimal('485.00')
            
            # Test to_dict method
            assert hasattr(payment, 'to_dict')
            payment_dict = payment.to_dict()
            assert isinstance(payment_dict, dict)
            assert 'amount' in payment_dict
            assert 'invoice_id' in payment_dict
    
    def test_payment_filter_functionality(self, client, app, setup_payment_test_data):
        """Test payment filtering functionality"""
        with client:
            user = setup_payment_test_data['user']
            invoice = setup_payment_test_data['invoice']
            
            # Login
            client.post('/login', data={'username': user.username}, follow_redirects=True)
            
            # Create test payments with different statuses
            with app.app_context():
                payment1 = Payment(
                    invoice_id=invoice.id,
                    amount=Decimal('100.00'),
                    currency='EUR',
                    payment_date=date.today(),
                    method='cash',
                    status='completed'
                )
                payment2 = Payment(
                    invoice_id=invoice.id,
                    amount=Decimal('200.00'),
                    currency='EUR',
                    payment_date=date.today(),
                    method='bank_transfer',
                    status='pending'
                )
                
                db.session.add_all([payment1, payment2])
                db.session.commit()
                
                # Test filter by status
                response = client.get('/payments?status=completed')
                assert response.status_code == 200
                
                # Test filter by method
                response = client.get('/payments?method=cash')
                assert response.status_code == 200
                
                # Cleanup
                db.session.delete(payment1)
                db.session.delete(payment2)
                db.session.commit()
    
    def test_invoice_shows_payment_history(self, client, app, setup_payment_test_data):
        """Test that invoice view shows payment history"""
        with client:
            user = setup_payment_test_data['user']
            invoice = setup_payment_test_data['invoice']
            
            # Login
            client.post('/login', data={'username': user.username}, follow_redirects=True)
            
            # Create payment
            with app.app_context():
                payment = Payment(
                    invoice_id=invoice.id,
                    amount=Decimal('500.00'),
                    currency='EUR',
                    payment_date=date.today(),
                    status='completed'
                )
                db.session.add(payment)
                db.session.commit()
                
                # View invoice
                response = client.get(f'/invoices/{invoice.id}')
                assert response.status_code == 200
                # Check if payment history section exists in response
                assert b'Payment History' in response.data or b'payment' in response.data.lower()
                
                # Cleanup
                db.session.delete(payment)
                db.session.commit()


class TestPaymentFeatureCompleteness:
    """Tests to ensure payment feature is complete"""
    
    def test_migration_exists(self):
        """Test that payment migration file exists"""
        import os
        
        migration_dir = os.path.join(os.path.dirname(__file__), '..', 'migrations', 'versions')
        migration_files = os.listdir(migration_dir)
        
        # Check for payment-related migration
        payment_migrations = [f for f in migration_files if 'payment' in f.lower()]
        assert len(payment_migrations) > 0, "No payment migration found"
    
    def test_payment_api_endpoint_exists(self, app):
        """Test that payment API endpoints exist"""
        with app.app_context():
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            assert any('payments' in rule and 'api' in rule for rule in rules)
    
    def test_all_crud_operations_work(self, client, app, setup_payment_test_data):
        """Test that all CRUD operations for payments work"""
        with client:
            user = setup_payment_test_data['user']
            invoice = setup_payment_test_data['invoice']
            
            # Login
            client.post('/login', data={'username': user.username}, follow_redirects=True)
            
            # CREATE
            payment_data = {
                'invoice_id': invoice.id,
                'amount': '300.00',
                'currency': 'EUR',
                'payment_date': date.today().strftime('%Y-%m-%d'),
                'method': 'cash',
                'status': 'completed'
            }
            
            create_response = client.post('/payments/create', data=payment_data, follow_redirects=True)
            assert create_response.status_code == 200
            
            with app.app_context():
                payment = Payment.query.filter_by(invoice_id=invoice.id, method='cash').first()
                assert payment is not None
                payment_id = payment.id
                
                # READ
                read_response = client.get(f'/payments/{payment_id}')
                assert read_response.status_code == 200
                
                # UPDATE
                update_data = {
                    'amount': '350.00',
                    'currency': 'EUR',
                    'payment_date': date.today().strftime('%Y-%m-%d'),
                    'method': 'bank_transfer',
                    'status': 'completed'
                }
                
                update_response = client.post(f'/payments/{payment_id}/edit', data=update_data, follow_redirects=True)
                assert update_response.status_code == 200
                
                # Verify update
                db.session.refresh(payment)
                assert payment.amount == Decimal('350.00')
                assert payment.method == 'bank_transfer'
                
                # DELETE
                delete_response = client.post(f'/payments/{payment_id}/delete', follow_redirects=True)
                assert delete_response.status_code == 200
                
                # Verify deletion
                deleted_payment = Payment.query.get(payment_id)
                assert deleted_payment is None

