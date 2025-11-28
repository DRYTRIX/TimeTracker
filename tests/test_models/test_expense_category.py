"""
Tests for ExpenseCategory model
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from app import db
from app.models import ExpenseCategory, Expense, User
from factories import UserFactory, ExpenseFactory, ExpenseCategoryFactory


@pytest.fixture
def user(client):
    """Create a test user"""
    user = UserFactory()
    try:
        user.set_password("password123")
    except Exception:
        pass
    return user


@pytest.fixture
def category(client):
    """Create a test expense category"""
    category = ExpenseCategoryFactory(
        name="Travel",
        code="TRV",
        monthly_budget=5000,
        quarterly_budget=15000,
        yearly_budget=60000,
        budget_threshold_percent=80,
        requires_receipt=True,
        requires_approval=True,
        is_active=True,
    )
    db.session.add(category)
    db.session.commit()
    return category


def test_create_expense_category(client):
    """Test creating an expense category"""
    category = ExpenseCategoryFactory(
        name="Meals", code="MEL", description="Meal expenses", monthly_budget=1000, requires_receipt=True
    )
    db.session.add(category)
    db.session.commit()

    assert category.id is not None
    assert category.name == "Meals"
    assert category.code == "MEL"
    assert category.monthly_budget == Decimal("1000")
    assert category.requires_receipt is True
    assert category.is_active is True


def test_category_budget_utilization(client, category, user):
    """Test budget utilization calculation"""
    # Create some approved expenses in current month
    today = date.today()
    start_of_month = date(today.year, today.month, 1)

    expense1 = ExpenseFactory(
        user_id=user.id, title="Flight tickets", category="Travel", amount=2000, expense_date=today, status="approved"
    )
    expense2 = ExpenseFactory(
        user_id=user.id, title="Hotel", category="Travel", amount=1500, expense_date=today, status="approved"
    )

    db.session.add_all([expense1, expense2])
    db.session.commit()

    # Get monthly utilization
    util = category.get_budget_utilization("monthly")

    assert util is not None
    assert util["budget"] == 5000
    assert util["spent"] == 3500
    assert util["utilization_percent"] == 70.0
    assert util["remaining"] == 1500
    assert util["over_threshold"] is False


def test_category_over_budget_threshold(client, category, user):
    """Test detecting when budget threshold is exceeded"""
    today = date.today()

    # Create expense that exceeds threshold (80% of 5000 = 4000)
    expense = ExpenseFactory(
        user_id=user.id, title="Expensive trip", category="Travel", amount=4500, expense_date=today, status="approved"
    )

    db.session.add(expense)
    db.session.commit()

    # Get monthly utilization
    util = category.get_budget_utilization("monthly")

    assert util is not None
    assert util["utilization_percent"] == 90.0
    assert util["over_threshold"] is True


def test_get_active_categories(client, category):
    """Test getting active categories"""
    # Create an inactive category
    inactive_category = ExpenseCategoryFactory(name="Deprecated", code="DEP", is_active=False)
    db.session.add(inactive_category)
    db.session.commit()

    # Get active categories
    active_categories = ExpenseCategory.get_active_categories()

    assert len(active_categories) >= 1
    assert category in active_categories
    assert inactive_category not in active_categories


def test_category_to_dict(client, category):
    """Test converting category to dictionary"""
    data = category.to_dict()

    assert data["id"] == category.id
    assert data["name"] == "Travel"
    assert data["code"] == "TRV"
    assert data["monthly_budget"] == 5000
    assert data["quarterly_budget"] == 15000
    assert data["yearly_budget"] == 60000
    assert data["budget_threshold_percent"] == 80
    assert data["requires_receipt"] is True
    assert data["requires_approval"] is True
    assert data["is_active"] is True


def test_category_unique_name(client, category):
    """Test that category names must be unique"""
    duplicate = ExpenseCategory(name="Travel", code="TRV2")  # Same as existing category
    db.session.add(duplicate)

    with pytest.raises(Exception):  # IntegrityError
        db.session.commit()


def test_category_quarterly_budget(client, category, user):
    """Test quarterly budget utilization"""
    today = date.today()
    quarter = (today.month - 1) // 3 + 1
    start_month = (quarter - 1) * 3 + 1

    # Create expenses in current quarter
    expense = ExpenseFactory(
        user_id=user.id, title="Q1 Travel", category="Travel", amount=8000, expense_date=today, status="approved"
    )

    db.session.add(expense)
    db.session.commit()

    # Get quarterly utilization
    util = category.get_budget_utilization("quarterly")

    assert util is not None
    assert util["budget"] == 15000
    assert util["spent"] == 8000
    assert util["utilization_percent"] == pytest.approx(53.33, rel=0.1)


def test_get_categories_over_budget(client, category, user):
    """Test getting categories over budget threshold"""
    today = date.today()

    # Create expense that exceeds threshold
    expense = ExpenseFactory(
        user_id=user.id, title="Over budget", category="Travel", amount=4500, expense_date=today, status="approved"
    )

    db.session.add(expense)
    db.session.commit()

    # Get categories over budget
    over_budget = ExpenseCategory.get_categories_over_budget("monthly")

    assert len(over_budget) > 0
    assert any(item["category"].id == category.id for item in over_budget)
