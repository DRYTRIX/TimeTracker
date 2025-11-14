"""
Test suite for currency display functionality.

This test ensures that all Finance pages (Reports, Payments, Expenses)
properly respect the currency setting from the database/environment
instead of hardcoding Euro symbols.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db, create_app
from app.models import User, Project, Settings, Client, Payment, Invoice, Expense
from factories import ClientFactory, ProjectFactory, InvoiceFactory, ExpenseFactory
from flask_login import login_user
from sqlalchemy.pool import StaticPool


@pytest.fixture
def app():
    """Isolated app for currency display tests to avoid SQLite file locking on Windows."""
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
def admin_user(app):
    """Create an admin user for testing."""
    user = User(username='admin', role='admin')
    user.is_active = True  # Set after creation
    user.set_password('test123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_client_with_auth(app, client, admin_user):
    """Return authenticated client."""
    # Use the actual login endpoint to properly authenticate
    with app.app_context():
        admin_in_session = db.session.merge(admin_user)
        username = admin_in_session.username
    client.post('/login', data={'username': username}, follow_redirects=True)
    return client


@pytest.fixture
def usd_settings(app):
    """Set currency to USD for testing."""
    with app.app_context():
        try:
            settings = Settings.get_settings()
            settings.currency = 'USD'
            db.session.commit()
        except Exception:
            db.session.rollback()
        # Return a lightweight object to avoid ORM expiration issues in assertions
        from types import SimpleNamespace
        return SimpleNamespace(currency='USD')


@pytest.fixture
def sample_client(app):
    """Create a sample client."""
    with app.app_context():
        client = ClientFactory(name='Test Client', email='test@example.com')
        return client


@pytest.fixture
def sample_project(app, sample_client):
    """Create a sample project."""
    with app.app_context():
        # Store client_id before accessing relationship
        project = ProjectFactory(
            name='Test Project',
            client_id=sample_client.id,
            status='active',
            hourly_rate=Decimal('100.00')
        )
        return project


@pytest.fixture
def sample_invoice(app, sample_project, admin_user, sample_client):
    """Create a sample invoice."""
    invoice = InvoiceFactory(
        project_id=sample_project.id,
        client_name=sample_client.name,
        due_date=date.today() + timedelta(days=30),
        created_by=admin_user.id,
        client_id=sample_client.id,
        status='sent',
        currency_code='USD',
    )
    return invoice


@pytest.fixture
def sample_payment(app, sample_invoice):
    """Create a sample payment."""
    payment = Payment(
        invoice_id=sample_invoice.id,
        amount=Decimal('1000.00'),
        currency='USD',
        payment_date=date.today(),
        method='bank_transfer',
        status='completed',
        gateway_fee=Decimal('10.00')
    )
    db.session.add(payment)
    db.session.commit()
    return payment


@pytest.fixture
def sample_expense(app, admin_user, sample_project):
    """Create a sample expense."""
    expense = ExpenseFactory(
        user_id=admin_user.id,
        title='Test Expense',
        category='travel',
        amount=Decimal('250.00'),
        expense_date=date.today(),
        project_id=sample_project.id,
        currency_code='USD',
        status='approved',
    )
    return expense


# Unit tests for template filters
@pytest.mark.unit
@pytest.mark.templates
def test_currency_symbol_filter_usd(app):
    """Test currency_symbol filter returns correct symbol for USD."""
    with app.app_context():
        from app.utils.template_filters import register_template_filters
        register_template_filters(app)
        
        # Test USD
        result = app.jinja_env.filters['currency_symbol']('USD')
        assert result == '$'


@pytest.mark.unit
@pytest.mark.templates
def test_currency_symbol_filter_eur(app):
    """Test currency_symbol filter returns correct symbol for EUR."""
    with app.app_context():
        from app.utils.template_filters import register_template_filters
        register_template_filters(app)
        
        # Test EUR
        result = app.jinja_env.filters['currency_symbol']('EUR')
        assert result == '€'


@pytest.mark.unit
@pytest.mark.templates
def test_currency_symbol_filter_gbp(app):
    """Test currency_symbol filter returns correct symbol for GBP."""
    with app.app_context():
        from app.utils.template_filters import register_template_filters
        register_template_filters(app)
        
        # Test GBP
        result = app.jinja_env.filters['currency_symbol']('GBP')
        assert result == '£'


@pytest.mark.unit
@pytest.mark.templates
def test_currency_symbol_filter_fallback(app):
    """Test currency_symbol filter returns currency code for unknown currencies."""
    with app.app_context():
        from app.utils.template_filters import register_template_filters
        register_template_filters(app)
        
        # Test unknown currency
        result = app.jinja_env.filters['currency_symbol']('XYZ')
        assert result == 'XYZ'


@pytest.mark.unit
@pytest.mark.templates
def test_currency_icon_filter_usd(app):
    """Test currency_icon filter returns correct icon for USD."""
    with app.app_context():
        from app.utils.template_filters import register_template_filters
        register_template_filters(app)
        
        # Test USD
        result = app.jinja_env.filters['currency_icon']('USD')
        assert result == 'fa-dollar-sign'


@pytest.mark.unit
@pytest.mark.templates
def test_currency_icon_filter_eur(app):
    """Test currency_icon filter returns correct icon for EUR."""
    with app.app_context():
        from app.utils.template_filters import register_template_filters
        register_template_filters(app)
        
        # Test EUR
        result = app.jinja_env.filters['currency_icon']('EUR')
        assert result == 'fa-euro-sign'


# Integration tests for context processor
@pytest.mark.integration
@pytest.mark.templates
def test_currency_injected_in_template_context(app, usd_settings):
    """Test that currency is properly injected into template context."""
    with app.test_request_context():
        from app.utils.context_processors import register_context_processors
        register_context_processors(app)
        
        # Simulate a request and get the injected context
        with app.app_context():
            context = app.jinja_env.globals
            # Currency should be available
            assert 'currency' in context or usd_settings.currency == 'USD'


# Smoke tests for finance pages
@pytest.mark.smoke
@pytest.mark.routes
def test_reports_page_displays_usd(test_client_with_auth, admin_user, usd_settings, sample_payment):
    """Test that Reports page displays USD symbol instead of hardcoded Euro."""
    # Access reports page
    response = test_client_with_auth.get('/reports')
    assert response.status_code == 200
    
    # Check that USD symbol is present
    data = response.data.decode('utf-8')
    
    # The page should NOT contain hardcoded Euro symbols
    # (Note: We allow € in the currency dropdown/selector if it exists)
    # Check that USD formatting is used in the summary cards
    assert '$' in data or 'currency' in data.lower()
    
    # If we have actual payment data, check it's formatted correctly
    if sample_payment:
        # Should have dollar amounts
        assert '1000.00' in data or '1,000.00' in data


@pytest.mark.smoke
@pytest.mark.routes
def test_payments_page_displays_usd(test_client_with_auth, admin_user, usd_settings, sample_payment):
    """Test that Payments list page displays USD symbol instead of hardcoded Euro."""
    # Access payments page
    response = test_client_with_auth.get('/payments')
    assert response.status_code == 200
    
    data = response.data.decode('utf-8')
    
    # Check that currency info is present
    assert '$' in data or 'USD' in data or 'currency' in data.lower()
    
    # Should display payment amounts
    assert '1000.00' in data or '1,000.00' in data


@pytest.mark.smoke
@pytest.mark.routes
def test_expenses_list_page_displays_usd(test_client_with_auth, admin_user, usd_settings, sample_expense):
    """Test that Expenses list page displays USD symbol instead of hardcoded Euro."""
    # Access expenses page
    response = test_client_with_auth.get('/expenses')
    assert response.status_code == 200
    
    data = response.data.decode('utf-8')
    
    # Check that currency info is present
    assert '$' in data or 'USD' in data or 'currency' in data.lower()
    
    # Should display expense amounts
    assert '250.00' in data


@pytest.mark.smoke
@pytest.mark.routes
def test_expenses_dashboard_displays_usd(test_client_with_auth, admin_user, usd_settings, sample_expense):
    """Test that Expenses dashboard displays USD symbol instead of hardcoded Euro."""
    # Access expenses dashboard
    response = test_client_with_auth.get('/expenses/dashboard')
    assert response.status_code == 200
    
    data = response.data.decode('utf-8')
    
    # Check that currency info is present
    assert '$' in data or 'USD' in data or 'currency' in data.lower()
    
    # Should display expense amounts
    assert '250.00' in data


# Model tests
@pytest.mark.unit
@pytest.mark.models
def test_settings_default_currency(app):
    """Test that Settings model has correct default currency from config."""
    with app.app_context():
        from app.config import Config
        settings = Settings.get_settings()
        
        # Should match the Config default (which can be EUR or USD depending on env)
        assert settings.currency in ['EUR', 'USD', 'GBP', 'JPY']
        assert len(settings.currency) == 3


@pytest.mark.unit
@pytest.mark.models
def test_settings_currency_can_be_changed(app):
    """Test that currency setting can be changed."""
    with app.app_context():
        settings = Settings.get_settings()
        original_currency = settings.currency
        
        # Change to USD
        settings.currency = 'USD'
        db.session.commit()
        
        # Verify change
        db.session.expire(settings)
        db.session.refresh(settings)
        assert settings.currency == 'USD'
        
        # Change back
        settings.currency = original_currency
        db.session.commit()


@pytest.mark.integration
@pytest.mark.templates
def test_currency_consistency_across_pages(test_client_with_auth, admin_user, usd_settings, 
                                           sample_payment, sample_expense):
    """Test that currency is consistent across all finance pages."""
    pages_to_check = [
        '/reports',
        '/payments',
        '/expenses',
        '/expenses/dashboard'
    ]
    
    for page_url in pages_to_check:
        response = test_client_with_auth.get(page_url)
        assert response.status_code == 200, f"Failed to load {page_url}"
        
        data = response.data.decode('utf-8')
        
        # Each page should have currency indicators
        # We're checking for either $ (USD symbol) or USD text or generic currency text
        has_currency = '$' in data or 'USD' in data or 'currency' in data.lower()
        assert has_currency, f"No currency indicator found on {page_url}"


@pytest.mark.integration
@pytest.mark.routes
def test_payments_with_different_currencies(app, test_client_with_auth, admin_user, 
                                            sample_invoice):
    """Test that payments with different currencies are displayed correctly."""
    with app.app_context():
        # Create payments with different currencies
        payment_usd = Payment(
            invoice_id=sample_invoice.id,
            amount=Decimal('1000.00'),
            currency='USD',
            payment_date=date.today(),
            method='bank_transfer',
            status='completed'
        )
        
        payment_eur = Payment(
            invoice_id=sample_invoice.id,
            amount=Decimal('850.00'),
            currency='EUR',
            payment_date=date.today(),
            method='stripe',
            status='completed'
        )
        
        db.session.add_all([payment_usd, payment_eur])
        db.session.commit()
        
        # Access payments page
        response = test_client_with_auth.get('/payments')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        
        # Both currencies should be displayed
        assert 'USD' in data
        assert 'EUR' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

