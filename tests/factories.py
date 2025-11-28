"""
Reusable model factories for tests.
Requires factory_boy and Faker (declared in requirements-test.txt).
"""

import datetime as _dt
from decimal import Decimal
import factory
from factory.alchemy import SQLAlchemyModelFactory

from app import db
from app.models import (
    User,
    Client,
    Project,
    TimeEntry,
    Invoice,
    InvoiceItem,
    Expense,
    Task,
    Payment,
    ExpenseCategory,
)


class _SessionFactory(SQLAlchemyModelFactory):
    """Base factory wired to Flask-SQLAlchemy session."""

    class Meta:
        abstract = True
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "flush"


class UserFactory(_SessionFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    role = "user"
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")


class ClientFactory(_SessionFactory):
    class Meta:
        model = Client

    name = factory.Sequence(lambda n: f"Client {n}")
    email = factory.LazyAttribute(lambda o: f"{o.name.lower().replace(' ', '')}@example.com")
    default_hourly_rate = Decimal("80.00")


class ProjectFactory(_SessionFactory):
    class Meta:
        model = Project

    name = factory.Sequence(lambda n: f"Project {n}")

    @factory.lazy_attribute
    def client_id(self):
        client = ClientFactory()
        # Ensure id is populated
        db.session.flush()
        return client.id

    description = factory.Faker("sentence")
    billable = True
    hourly_rate = Decimal("75.00")
    status = "active"


class UserTaskFactory(_SessionFactory):
    class Meta:
        model = Task

    name = factory.Sequence(lambda n: f"Task {n}")
    description = factory.Faker("sentence")
    project = factory.SubFactory(ProjectFactory)
    created_by = factory.SubFactory(UserFactory)
    priority = "medium"


class TimeEntryFactory(_SessionFactory):
    class Meta:
        model = TimeEntry

    user_fk = factory.SubFactory(UserFactory)
    project_fk = factory.SubFactory(ProjectFactory)
    user_id = factory.SelfAttribute("user_fk.id")
    project_id = factory.SelfAttribute("project_fk.id")
    start_time = factory.LazyFunction(lambda: _dt.datetime.now() - _dt.timedelta(hours=2))
    end_time = factory.LazyFunction(lambda: _dt.datetime.now())
    notes = factory.Faker("sentence")
    tags = "test,automation"
    source = "manual"
    billable = True


class InvoiceFactory(_SessionFactory):
    class Meta:
        model = Invoice

    project_fk = factory.SubFactory(ProjectFactory)
    invoice_number = factory.LazyFunction(
        lambda: (
            Invoice.generate_invoice_number()
            if hasattr(Invoice, "generate_invoice_number")
            else f"INV-{_dt.datetime.utcnow().strftime('%Y%m%d')}-001"
        )
    )
    project_id = factory.SelfAttribute("project_fk.id")
    client_id = factory.SelfAttribute("project_fk.client_id")
    client_name = factory.LazyAttribute(lambda o: db.session.get(Client, o.client_id).name if o.client_id else "Client")
    created_by = factory.LazyAttribute(lambda o: UserFactory().id)
    tax_rate = Decimal("20.00")
    issue_date = factory.LazyFunction(lambda: _dt.date.today())
    due_date = factory.LazyFunction(lambda: _dt.date.today() + _dt.timedelta(days=30))
    status = "draft"


class InvoiceItemFactory(_SessionFactory):
    class Meta:
        model = InvoiceItem

    # By default, create a backing invoice; tests may override invoice_id explicitly.
    invoice_id = factory.LazyAttribute(lambda o: InvoiceFactory().id)
    description = factory.Faker("sentence")
    quantity = Decimal("1.00")
    unit_price = Decimal("50.00")


class ExpenseFactory(_SessionFactory):
    class Meta:
        model = Expense

    user_fk = factory.SubFactory(UserFactory)
    project_fk = factory.SubFactory(ProjectFactory)
    user_id = factory.SelfAttribute("user_fk.id")
    project_id = factory.SelfAttribute("project_fk.id")
    client_id = factory.SelfAttribute("project_fk.client_id")
    title = factory.Faker("sentence", nb_words=3)
    category = "other"
    amount = Decimal("10.00")
    expense_date = factory.LazyFunction(lambda: _dt.date.today())
    billable = False
    reimbursable = True


class PaymentFactory(_SessionFactory):
    class Meta:
        model = Payment

    # Ensure an invoice exists by default; tests can override invoice_id explicitly.
    invoice_id = factory.LazyAttribute(lambda _: InvoiceFactory().id)
    amount = Decimal("100.00")
    currency = "EUR"
    payment_date = factory.LazyFunction(lambda: _dt.date.today())
    method = "bank_transfer"
    reference = factory.Sequence(lambda n: f"PAY-REF-{n:04d}")
    status = "completed"
    received_by = factory.LazyAttribute(lambda _: UserFactory().id)


class ExpenseCategoryFactory(_SessionFactory):
    class Meta:
        model = ExpenseCategory

    name = factory.Sequence(lambda n: f"Category {n}")
    code = factory.Sequence(lambda n: f"C{n:03d}")
    monthly_budget = Decimal("5000")
    quarterly_budget = Decimal("15000")
    yearly_budget = Decimal("60000")
    budget_threshold_percent = 80
    requires_receipt = True
    requires_approval = True
    is_active = True
