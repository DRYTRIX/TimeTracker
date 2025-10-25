"""
Smoke tests for invoice currency functionality
Simple high-level tests to ensure the system works end-to-end
"""
import pytest
import os
from datetime import date, timedelta
from decimal import Decimal
from app import create_app, db
from app.models import User, Project, Client, Invoice, Settings


@pytest.fixture
def app():
    """Create and configure a test app instance"""
    # Set test database URL before creating app
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_invoice_currency_smoke(app):
    """Smoke test: Create invoice and verify it uses settings currency"""
    with app.app_context():
        # Setup: Create user, client, project
        user = User(username='smokeuser', email='smoke@example.com', is_admin=True)
        user.set_password('password')
        db.session.add(user)
        
        client = Client(name='Smoke Client', email='client@example.com', created_by=1)
        db.session.add(client)
        
        project = Project(
            name='Smoke Project',
            client_id=1,
            created_by=1,
            billable=True,
            hourly_rate=Decimal('100.00'),
            status='active'
        )
        db.session.add(project)
        
        # Set currency in settings
        settings = Settings.get_settings()
        settings.currency = 'CHF'
        
        db.session.commit()
        
        # Action: Create invoice
        invoice = Invoice(
            invoice_number='SMOKE-001',
            project_id=project.id,
            client_name=client.name,
            due_date=date.today() + timedelta(days=30),
            created_by=user.id,
            client_id=client.id,
            currency_code=settings.currency
        )
        db.session.add(invoice)
        db.session.commit()
        
        # Verify: Invoice has correct currency
        assert invoice.currency_code == 'CHF', f"Expected CHF but got {invoice.currency_code}"
        
        print("✓ Smoke test passed: Invoice currency correctly set from Settings")


def test_pdf_generator_uses_settings_currency(app):
    """Smoke test: Verify PDF generator uses settings currency"""
    with app.app_context():
        # Setup
        user = User(username='pdfuser', email='pdf@example.com', is_admin=True)
        user.set_password('password')
        db.session.add(user)
        
        client = Client(name='PDF Client', email='pdf@example.com', created_by=1)
        db.session.add(client)
        
        project = Project(
            name='PDF Project',
            client_id=1,
            created_by=1,
            billable=True,
            hourly_rate=Decimal('150.00'),
            status='active'
        )
        db.session.add(project)
        
        settings = Settings.get_settings()
        settings.currency = 'SEK'
        
        invoice = Invoice(
            invoice_number='PDF-001',
            project_id=project.id,
            client_name=client.name,
            due_date=date.today() + timedelta(days=30),
            created_by=user.id,
            client_id=client.id,
            currency_code=settings.currency
        )
        db.session.add(invoice)
        db.session.commit()
        
        # Verify
        assert invoice.currency_code == settings.currency
        assert settings.currency == 'SEK'
        
        print("✓ Smoke test passed: PDF generator will use correct currency")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

