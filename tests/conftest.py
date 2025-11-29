"""
Pytest configuration and shared fixtures for TimeTracker tests.
This file contains common fixtures and test configuration used across all test modules.
"""

import pytest
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.pool import NullPool

from app import create_app, db

# Import all models to ensure their tables are created by db.create_all()
from app.models import (
    User,
    Project,
    TimeEntry,
    Client,
    Settings,
    Invoice,
    InvoiceItem,
    Task,
    TaskActivity,
    Comment,
    ExpenseCategory,
    Mileage,
    PerDiem,
    PerDiemRate,
    ExtraGood,
    FocusSession,
    RecurringBlock,
    RateOverride,
    SavedFilter,
    ProjectCost,
    KanbanColumn,
    TimeEntryTemplate,
    Activity,
    UserFavoriteProject,
    ClientNote,
    WeeklyTimeGoal,
    Expense,
    Permission,
    Role,
    ApiToken,
    CalendarEvent,
    BudgetAlert,
    DataImport,
    DataExport,
    InvoicePDFTemplate,
    ClientPrepaidConsumption,
    AuditLog,
    RecurringInvoice,
    InvoiceEmail,
    Webhook,
    WebhookDelivery,
    InvoiceTemplate,
    Currency,
    ExchangeRate,
    TaxRule,
    Payment,
    CreditNote,
    InvoiceReminderSchedule,
    SavedReportView,
    ReportEmailSchedule,
    Warehouse,
    StockItem,
    WarehouseStock,
    StockMovement,
    StockReservation,
    ProjectStockAllocation,
    Quote,
    QuoteItem,
)


# ----------------------------------------------------------------------------
# Time control helpers (freezegun)
# ----------------------------------------------------------------------------
@pytest.fixture
def time_freezer():
    """
    Utility fixture to freeze time during a test.

    Usage:
        freezer = time_freezer()  # freezes at default "2024-01-01 09:00:00"
        # ... run code ...
        freezer.stop()

        # or with a custom timestamp:
        f = time_freezer("2024-06-15 12:30:00")
        # ... run code ...
        f.stop()
    """
    from freezegun import freeze_time as _freeze_time

    _active = []

    def _start(at: str = "2024-01-01 09:00:00"):
        f = _freeze_time(at)
        f.start()
        _active.append(f)
        return f

    try:
        yield _start
    finally:
        while _active:
            f = _active.pop()
            try:
                f.stop()
            except Exception:
                pass


# ============================================================================
# Application Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def app_config():
    """Base test configuration."""
    return {
        "TESTING": True,
        # Use file-based SQLite to ensure consistent connections across contexts/threads
        "SQLALCHEMY_DATABASE_URI": "sqlite:///pytest_main.sqlite",
        # Mitigate SQLite 'database is locked' by increasing busy timeout and enabling pre-ping
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "pool_pre_ping": True,
            "connect_args": {"timeout": 30},
            "poolclass": NullPool,
        },
        "FLASK_ENV": "testing",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key-do-not-use-in-production",
        "SERVER_NAME": "localhost:5000",
        "APPLICATION_ROOT": "/",
        "PREFERRED_URL_SCHEME": "http",
        "SESSION_COOKIE_HTTPONLY": True,
        # Ensure a stable locale for Babel-dependent formatting in tests
        "BABEL_DEFAULT_LOCALE": "en",
    }


@pytest.fixture(scope="function")
def app(app_config):
    """Create application for testing with function scope."""
    # Use a unique SQLite file per test function to avoid Windows file locking
    unique_db_path = os.path.join(tempfile.gettempdir(), f"pytest_{uuid.uuid4().hex}.sqlite")
    config = dict(app_config)
    config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{unique_db_path}"
    app = create_app(config)

    with app.app_context():
        # Import all models AFTER app creation but BEFORE db.create_all()
        # This ensures they're registered with SQLAlchemy's metadata
        # Import all models explicitly to ensure their tables are created
        from app.models import (
            User,
            Project,
            TimeEntry,
            Client,
            Settings,
            Invoice,
            InvoiceItem,
            Task,
            TaskActivity,
            Comment,
            ExpenseCategory,
            Mileage,
            PerDiem,
            PerDiemRate,
            ExtraGood,
            FocusSession,
            RecurringBlock,
            RateOverride,
            SavedFilter,
            ProjectCost,
            KanbanColumn,
            TimeEntryTemplate,
            Activity,
            UserFavoriteProject,
            ClientNote,
            WeeklyTimeGoal,
            Expense,
            Permission,
            Role,
            ApiToken,
            CalendarEvent,
            BudgetAlert,
            DataImport,
            DataExport,
            InvoicePDFTemplate,
            ClientPrepaidConsumption,
            AuditLog,
            RecurringInvoice,
            InvoiceEmail,
            Webhook,
            WebhookDelivery,
            InvoiceTemplate,
            Currency,
            ExchangeRate,
            TaxRule,
            Payment,
            CreditNote,
            InvoiceReminderSchedule,
            SavedReportView,
            ReportEmailSchedule,
        )

        # Ensure any lingering connections are closed to avoid SQLite file locks (Windows)
        try:
            db.engine.dispose()
        except Exception:
            pass
        # Drop all tables first to ensure clean state
        try:
            db.drop_all()
        except Exception:
            pass  # Ignore errors if tables don't exist

        # Create all tables, handling index creation errors gracefully
        # We need to create tables even if some indexes already exist
        # SQLAlchemy's create_all() stops on first error, so we need to handle this carefully
        try:
            db.create_all()
        except Exception as e:
            # SQLite may raise OperationalError if indexes already exist
            # This can happen if db.create_all() is called multiple times
            error_msg = str(e).lower()
            if "index" in error_msg and ("already exists" in error_msg or "duplicate" in error_msg):
                # Index already exists - this is okay, but we need to ensure all tables are created
                # Create tables individually to work around the issue
                from sqlalchemy import inspect

                inspector = inspect(db.engine)
                existing_tables = set(inspector.get_table_names())

                # Create missing tables explicitly
                for table_name, table in db.metadata.tables.items():
                    if table_name not in existing_tables:
                        try:
                            table.create(db.engine, checkfirst=True)
                        except Exception as table_error:
                            # Ignore errors for individual tables (might be index issues)
                            pass
            else:
                # Log other errors but try to continue
                import logging
                import traceback

                logger = logging.getLogger(__name__)
                logger.warning(f"Error during db.create_all(): {e}")
                logger.warning(traceback.format_exc())

        # Verify critical tables were created and create any missing ones
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        created_tables = set(inspector.get_table_names())
        required_tables = ["time_entries", "tasks", "users", "projects"]
        missing_tables = [t for t in required_tables if t not in created_tables]

        if missing_tables:
            # Try to create missing tables explicitly
            for table_name in missing_tables:
                if table_name in db.metadata.tables:
                    try:
                        db.metadata.tables[table_name].create(db.engine, checkfirst=True)
                    except Exception as e:
                        # Ignore errors - table might already exist or have dependency issues
                        pass

        # Create default settings
        settings = Settings()
        db.session.add(settings)
        db.session.commit()

        yield app

        db.session.remove()
        try:
            db.drop_all()
        except Exception:
            pass  # Ignore errors during cleanup
        try:
            db.engine.dispose()
        except Exception:
            pass
        # Remove the per-test database file
        try:
            if os.path.exists(unique_db_path):
                os.remove(unique_db_path)
        except Exception:
            pass


@pytest.fixture(scope="function")
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def db_session(app):
    """Create a database session for tests."""
    with app.app_context():
        yield db.session


# ============================================================================
# User Fixtures
# ============================================================================


@pytest.fixture
def user(app):
    """Create a regular test user."""
    # Idempotent: return existing test user if already present (PostgreSQL CI)
    try:
        existing = User.query.filter_by(username="testuser").first()
        if existing:
            if not existing.is_active:
                existing.is_active = True
                db.session.commit()
            db.session.refresh(existing)
            return existing
    except Exception:
        # Tables don't exist yet or other DB error, rollback and proceed to create user
        db.session.rollback()

    try:
        user = User(username="testuser", role="user", email="testuser@example.com")
        user.is_active = True  # Set after creation
        db.session.add(user)
        db.session.commit()

        # Refresh to ensure all relationships are loaded and object stays in session
        db.session.refresh(user)
        return user
    except Exception:
        # If tables still don't exist, try to create them
        db.session.rollback()
        db.create_all()

        # Try again after creating tables
        user = User(username="testuser", role="user", email="testuser@example.com")
        user.is_active = True  # Set after creation
        db.session.add(user)
        db.session.commit()

        db.session.refresh(user)
        return user


@pytest.fixture
def admin_user(app):
    """Create an admin test user."""
    # Idempotent: return existing admin user if already present (PostgreSQL CI)
    try:
        existing = User.query.filter_by(username="admin").first()
        if existing:
            if existing.role != "admin":
                existing.role = "admin"
                existing.is_active = True
                db.session.commit()
            db.session.refresh(existing)
            return existing
    except Exception:
        # Tables don't exist yet or other DB error, rollback and proceed to create admin
        db.session.rollback()

    try:
        admin = User(username="admin", role="admin", email="admin@example.com")
        admin.is_active = True  # Set after creation
        db.session.add(admin)
        db.session.commit()

        # Refresh to ensure all relationships are loaded and object stays in session
        db.session.refresh(admin)
        return admin
    except Exception:
        # If tables still don't exist, try to create them
        db.session.rollback()
        db.create_all()

        # Try again after creating tables
        admin = User(username="admin", role="admin", email="admin@example.com")
        admin.is_active = True  # Set after creation
        db.session.add(admin)
        db.session.commit()

        db.session.refresh(admin)
        return admin


@pytest.fixture
def auth_user(user):
    """Alias for user fixture (for backward compatibility with older tests)."""
    return user


@pytest.fixture
def multiple_users(app):
    """Create multiple test users."""
    users = []
    for i in range(1, 4):
        user = User(username=f"user{i}", role="user", email=f"user{i}@example.com")
        user.is_active = True  # Set after creation
        users.append(user)
    db.session.add_all(users)
    db.session.commit()

    for user in users:
        db.session.refresh(user)

    return users


# ============================================================================
# Client Fixtures
# ============================================================================


@pytest.fixture
def test_client(app, user):
    """Create a test client (business client, not test client)."""
    client_model = Client(
        name="Test Client Corp",
        description="Test client for integration tests",
        contact_person="John Doe",
        email="john@testclient.com",
        phone="+1 (555) 123-4567",
        address="123 Test Street, Test City, TC 12345",
        default_hourly_rate=Decimal("85.00"),
    )
    client_model.status = "active"  # Set after creation
    db.session.add(client_model)
    # Flush to assign primary key before commit to avoid expired attribute reloads
    db.session.flush()
    client_id = client_model.id
    db.session.commit()
    # Re-query to ensure we return a persistent instance without relying on refresh
    persisted_client = Client.query.get(client_id) or Client.query.filter_by(id=client_id).first()
    # Fallback to the original instance if re-query unexpectedly returns None
    return persisted_client or client_model


@pytest.fixture
def multiple_clients(app, user):
    """Create multiple test clients."""
    clients = []
    for i in range(1, 4):
        client = Client(
            name=f"Client {i}", email=f"client{i}@example.com", default_hourly_rate=Decimal("75.00") + Decimal(i * 10)
        )
        client.status = "active"  # Set after creation
        clients.append(client)
    db.session.add_all(clients)
    db.session.commit()

    for client in clients:
        db.session.refresh(client)

    return clients


# ============================================================================
# Project Fixtures
# ============================================================================


@pytest.fixture
def project(app, test_client):
    """Create a test project."""
    # Resolve client_id robustly to avoid issues with expired/detached instances
    try:
        cid = getattr(test_client, "id", None)
    except Exception:
        cid = None
    if not cid:
        existing = Client.query.filter_by(name="Test Client Corp").first() or Client.query.first()
        if existing:
            cid = existing.id
        else:
            fallback = Client(
                name="Test Client Corp", email="john@testclient.com", default_hourly_rate=Decimal("85.00")
            )
            fallback.status = "active"
            db.session.add(fallback)
            db.session.flush()
            cid = fallback.id

    project = Project(
        name="Test Project",
        client_id=cid,
        description="Test project description",
        billable=True,
        hourly_rate=Decimal("75.00"),
    )
    project.status = "active"  # Set after creation
    db.session.add(project)
    # Flush to assign ID before commit and return the same instance to avoid re-query issues
    db.session.flush()
    db.session.commit()
    return project


@pytest.fixture
def multiple_projects(app, test_client):
    """Create multiple test projects."""
    # Resolve client_id robustly
    try:
        cid = getattr(test_client, "id", None)
    except Exception:
        cid = None
    if not cid:
        existing = Client.query.filter_by(name="Test Client Corp").first() or Client.query.first()
        if existing:
            cid = existing.id
        else:
            fallback = Client(
                name="Test Client Corp", email="john@testclient.com", default_hourly_rate=Decimal("85.00")
            )
            fallback.status = "active"
            db.session.add(fallback)
            db.session.flush()
            cid = fallback.id

    projects = []
    for i in range(1, 4):
        project = Project(
            name=f"Project {i}",
            client_id=cid,
            description=f"Test project {i}",
            billable=True,
            hourly_rate=Decimal("75.00"),
        )
        project.status = "active"  # Set after creation
        projects.append(project)
    db.session.add_all(projects)
    db.session.commit()

    for proj in projects:
        db.session.refresh(proj)

    return projects


# ============================================================================
# Time Entry Fixtures
# ============================================================================


@pytest.fixture
def time_entry(app, user, project):
    """Create a single time entry."""
    start_time = datetime.utcnow() - timedelta(hours=2)
    end_time = datetime.utcnow()

    entry = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=start_time,
        end_time=end_time,
        notes="Test time entry",
        tags="test,development",
        source="manual",
        billable=True,
    )
    db.session.add(entry)
    db.session.commit()

    # Refresh entry, but handle case where related objects might be deleted
    try:
        db.session.refresh(entry)
    except Exception:
        # If refresh fails, just return the entry as-is
        # This can happen if user/project are deleted before this fixture is used
        pass
    return entry


@pytest.fixture
def multiple_time_entries(app, user, project):
    """Create multiple time entries."""
    base_time = datetime.utcnow() - timedelta(days=7)
    entries = []

    for i in range(5):
        start = base_time + timedelta(days=i, hours=9)
        end = base_time + timedelta(days=i, hours=17)

        entry = TimeEntry(
            user_id=user.id,
            project_id=project.id,
            start_time=start,
            end_time=end,
            notes=f"Work day {i+1}",
            tags="development,testing",
            source="manual",
            billable=True,
        )
        entries.append(entry)

    db.session.add_all(entries)
    db.session.commit()

    for entry in entries:
        db.session.refresh(entry)

    return entries


@pytest.fixture
def active_timer(app, user, project):
    """Create an active timer (time entry without end time)."""
    timer = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=datetime.utcnow(),
        notes="Active timer",
        source="auto",
        billable=True,
    )
    db.session.add(timer)
    db.session.commit()

    db.session.refresh(timer)
    return timer


# ============================================================================
# Task Fixtures
# ============================================================================


@pytest.fixture
def task(app, project, user):
    """Create a test task."""
    task = Task(
        name="Test Task",
        description="Test task description",
        project_id=project.id,
        priority="medium",
        created_by=user.id,
    )
    task.status = "todo"  # Set after creation
    db.session.add(task)
    db.session.commit()

    db.session.refresh(task)
    return task


# ============================================================================
# Invoice Fixtures
# ============================================================================


@pytest.fixture
def invoice(app, user, project, test_client):
    """Create a test invoice."""
    from datetime import date
    from factories import InvoiceFactory

    invoice = InvoiceFactory(
        invoice_number=Invoice.generate_invoice_number(),
        project_id=project.id,
        client_id=test_client.id,
        client_name=test_client.name,
        due_date=date.today() + timedelta(days=30),
        created_by=user.id,
        tax_rate=Decimal("20.00"),
        status="draft",
    )
    db.session.commit()

    db.session.refresh(invoice)
    return invoice


@pytest.fixture
def invoice_with_items(app, invoice):
    """Create an invoice with items."""
    from factories import InvoiceItemFactory

    items = [
        InvoiceItemFactory(
            invoice_id=invoice.id,
            description="Development work",
            quantity=Decimal("10.00"),
            unit_price=Decimal("75.00"),
        ),
        InvoiceItemFactory(
            invoice_id=invoice.id, description="Testing work", quantity=Decimal("5.00"), unit_price=Decimal("60.00")
        ),
    ]
    db.session.commit()

    invoice.calculate_totals()
    db.session.commit()

    db.session.refresh(invoice)
    for item in items:
        db.session.refresh(item)

    return invoice, items


# ============================================================================
# Authentication Fixtures
# ============================================================================


@pytest.fixture
def authenticated_client(client, user):
    """Create an authenticated test client."""
    # Use the actual login endpoint to properly authenticate
    # If CSRF is enabled, fetch a token and include it in the form submit
    try:
        from flask import current_app

        csrf_enabled = bool(current_app.config.get("WTF_CSRF_ENABLED"))
    except Exception:
        csrf_enabled = False

    login_data = {"username": user.username}
    headers = {}

    if csrf_enabled:
        try:
            resp = client.get("/auth/csrf-token")
            token = ""
            if resp.is_json:
                token = (resp.get_json() or {}).get("csrf_token") or ""
            login_data["csrf_token"] = token
            headers["X-CSRFToken"] = token
        except Exception:
            pass

    client.post("/login", data=login_data, headers=headers or None, follow_redirects=True)
    return client


@pytest.fixture
def admin_authenticated_client(client, admin_user):
    """Create an authenticated admin test client."""
    # Use the actual login endpoint to properly authenticate (same as authenticated_client)
    # If CSRF is enabled, fetch a token and include it in the form submit
    try:
        from flask import current_app

        csrf_enabled = bool(current_app.config.get("WTF_CSRF_ENABLED"))
    except Exception:
        csrf_enabled = False

    login_data = {"username": admin_user.username}
    headers = {}

    if csrf_enabled:
        try:
            resp = client.get("/auth/csrf-token")
            token = ""
            if resp.is_json:
                token = (resp.get_json() or {}).get("csrf_token") or ""
            login_data["csrf_token"] = token
            headers["X-CSRFToken"] = token
        except Exception:
            pass

    client.post("/login", data=login_data, headers=headers or None, follow_redirects=True)
    return client


@pytest.fixture
def auth_headers(user):
    """Create authentication headers for API tests (session-based)."""
    # Note: For tests that use headers, they should use authenticated_client instead
    # This fixture is here for backward compatibility
    return {}


@pytest.fixture
def regular_user(user):
    """Alias for user fixture (regular non-admin user)."""
    return user


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    fd, path = tempfile.mkstemp()
    yield path
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    dirpath = tempfile.mkdtemp()
    yield dirpath
    import shutil

    shutil.rmtree(dirpath)


# ============================================================================
# Alias Fixtures (for compatibility with different test naming conventions)
# ============================================================================


@pytest.fixture
def test_client_obj(test_client):
    """Alias for test_client to avoid naming conflicts"""
    return test_client


@pytest.fixture
def test_user(user):
    """Alias for user fixture"""
    return user


@pytest.fixture
def auth_user(user):
    """Alias for user fixture"""
    return user


@pytest.fixture
def test_project(project):
    """Alias for project fixture"""
    return project


@pytest.fixture
def test_task(task):
    """Alias for task fixture"""
    return task


# ============================================================================
# Installation Config Fixture
# ============================================================================


@pytest.fixture
def installation_config(temp_dir):
    """Create a temporary installation config for testing"""
    from app.utils.installation import InstallationConfig

    # Override the config directory to use temp directory
    original_config_dir = InstallationConfig.CONFIG_DIR
    InstallationConfig.CONFIG_DIR = temp_dir

    # Create the config instance
    config = InstallationConfig()

    yield config

    # Restore original config directory
    InstallationConfig.CONFIG_DIR = original_config_dir


# ============================================================================
# Pytest Markers
# ============================================================================


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "smoke: Quick smoke tests")
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "database: Database-related tests")
    config.addinivalue_line("markers", "models: Model tests")
    config.addinivalue_line("markers", "routes: Route tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
