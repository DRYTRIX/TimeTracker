"""
Tests for PerDiem and PerDiemRate models
"""

import pytest
from datetime import date, datetime, time
from decimal import Decimal
from app import db
from app.models import PerDiem, PerDiemRate, User


@pytest.fixture
def user(client):
    """Create a test user"""
    user = User(username="testuser", email="test@example.com")
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def rate(client):
    """Create a test per diem rate"""
    rate = PerDiemRate(
        country="Germany",
        city="Berlin",
        full_day_rate=28.00,
        half_day_rate=14.00,
        breakfast_rate=5.60,
        lunch_rate=11.20,
        dinner_rate=11.20,
        incidental_rate=3.00,
        currency_code="EUR",
        effective_from=date(2024, 1, 1),
    )
    db.session.add(rate)
    db.session.commit()
    return rate


def test_create_per_diem_rate(client):
    """Test creating a per diem rate"""
    rate = PerDiemRate(
        country="France", city="Paris", full_day_rate=45.00, half_day_rate=22.50, effective_from=date(2024, 1, 1)
    )

    db.session.add(rate)
    db.session.commit()

    assert rate.id is not None
    assert rate.country == "France"
    assert rate.city == "Paris"
    assert rate.full_day_rate == Decimal("45.00")
    assert rate.half_day_rate == Decimal("22.50")
    assert rate.is_active is True


def test_get_rate_for_location(client, rate):
    """Test getting rate for a specific location"""
    found_rate = PerDiemRate.get_rate_for_location("Germany", "Berlin", date.today())

    assert found_rate is not None
    assert found_rate.id == rate.id
    assert found_rate.city == "Berlin"


def test_get_rate_falls_back_to_country(client):
    """Test that rate search falls back to country rate if city not found"""
    # Create country-level rate
    country_rate = PerDiemRate(
        country="Netherlands",
        city=None,  # Country-level rate
        full_day_rate=35.00,
        half_day_rate=17.50,
        effective_from=date(2024, 1, 1),
    )
    db.session.add(country_rate)
    db.session.commit()

    # Search for a city that doesn't have a rate
    found_rate = PerDiemRate.get_rate_for_location("Netherlands", "Amsterdam", date.today())

    assert found_rate is not None
    assert found_rate.id == country_rate.id
    assert found_rate.city is None


def test_create_per_diem_claim(client, user, rate):
    """Test creating a per diem claim"""
    per_diem = PerDiem(
        user_id=user.id,
        trip_purpose="Conference",
        start_date=date(2025, 10, 20),
        end_date=date(2025, 10, 23),
        country="Germany",
        city="Berlin",
        full_day_rate=rate.full_day_rate,
        half_day_rate=rate.half_day_rate,
        full_days=3,
        half_days=1,
        breakfast_deduction=rate.breakfast_rate,
        currency_code="EUR",
    )

    db.session.add(per_diem)
    db.session.commit()

    assert per_diem.id is not None
    assert per_diem.trip_purpose == "Conference"
    assert per_diem.full_days == 3
    assert per_diem.half_days == 1
    assert per_diem.total_days == 3.5
    assert per_diem.status == "pending"


def test_per_diem_calculation(client, user, rate):
    """Test per diem amount calculation"""
    per_diem = PerDiem(
        user_id=user.id,
        trip_purpose="Business trip",
        start_date=date(2025, 10, 20),
        end_date=date(2025, 10, 22),
        country="Germany",
        city="Berlin",
        full_day_rate=28,
        half_day_rate=14,
        full_days=2,
        half_days=1,
        breakfast_provided=0,
        breakfast_deduction=0,
        lunch_deduction=0,
        dinner_deduction=0,
    )

    db.session.add(per_diem)
    db.session.commit()

    # Calculation: (2 * 28) + (1 * 14) = 56 + 14 = 70
    assert per_diem.calculated_amount == Decimal("70")


def test_per_diem_with_meal_deductions(client, user, rate):
    """Test per diem with provided meals"""
    per_diem = PerDiem(
        user_id=user.id,
        trip_purpose="Conference with meals",
        start_date=date(2025, 10, 20),
        end_date=date(2025, 10, 22),
        country="Germany",
        city="Berlin",
        full_day_rate=28,
        half_day_rate=14,
        full_days=3,
        half_days=0,
        breakfast_provided=2,
        lunch_provided=3,
        dinner_provided=2,
        breakfast_deduction=5.60,
        lunch_deduction=11.20,
        dinner_deduction=11.20,
    )

    db.session.add(per_diem)
    db.session.commit()

    # Calculation: (3 * 28) - (2 * 5.60) - (3 * 11.20) - (2 * 11.20)
    # = 84 - 11.20 - 33.60 - 22.40 = 16.80
    assert per_diem.calculated_amount == Decimal("16.80")


def test_calculate_days_from_dates_single_day(client):
    """Test calculating days for a single day trip"""
    result = PerDiem.calculate_days_from_dates(
        start_date=date(2025, 10, 20),
        end_date=date(2025, 10, 20),
        departure_time=time(8, 0),
        return_time=time(18, 0),  # 10 hours
    )

    assert result["full_days"] == 1
    assert result["half_days"] == 0


def test_calculate_days_from_dates_multi_day(client):
    """Test calculating days for multi-day trip"""
    result = PerDiem.calculate_days_from_dates(
        start_date=date(2025, 10, 20),
        end_date=date(2025, 10, 23),
        departure_time=time(8, 0),  # Before noon = full day
        return_time=time(14, 0),  # After noon = full day
    )

    # Day 1: departure before 12:00 = full day
    # Day 2-3: middle days = 2 full days
    # Day 4: return after 12:00 = full day
    # Total: 4 full days
    assert result["full_days"] == 4
    assert result["half_days"] == 0


def test_calculate_days_with_half_days(client):
    """Test calculating days with half days"""
    result = PerDiem.calculate_days_from_dates(
        start_date=date(2025, 10, 20),
        end_date=date(2025, 10, 22),
        departure_time=time(14, 0),  # After noon = half day
        return_time=time(10, 0),  # Before noon = half day
    )

    # Day 1: departure after 12:00 = half day
    # Day 2: middle day = full day
    # Day 3: return before 12:00 = half day
    # Total: 1 full day, 2 half days
    assert result["full_days"] == 1
    assert result["half_days"] == 2


def test_per_diem_approval(client, user):
    """Test per diem approval workflow"""
    admin = User(username="admin", email="admin@example.com", role="admin")
    admin.set_password("admin123")
    db.session.add(admin)
    db.session.commit()

    per_diem = PerDiem(
        user_id=user.id,
        trip_purpose="Business trip",
        start_date=date(2025, 10, 20),
        end_date=date(2025, 10, 22),
        country="Germany",
        full_day_rate=28,
        half_day_rate=14,
        full_days=2,
        half_days=1,
    )

    db.session.add(per_diem)
    db.session.commit()

    # Approve
    per_diem.approve(admin.id, notes="Approved")
    db.session.commit()

    assert per_diem.status == "approved"
    assert per_diem.approved_by == admin.id
    assert per_diem.approved_at is not None


def test_per_diem_to_dict(client, user, rate):
    """Test converting per diem to dictionary"""
    per_diem = PerDiem(
        user_id=user.id,
        trip_purpose="Test trip",
        start_date=date(2025, 10, 20),
        end_date=date(2025, 10, 22),
        country="Germany",
        city="Berlin",
        full_day_rate=28,
        half_day_rate=14,
        full_days=2,
        half_days=1,
    )

    db.session.add(per_diem)
    db.session.commit()

    data = per_diem.to_dict()

    assert data["id"] == per_diem.id
    assert data["user_id"] == user.id
    assert data["trip_purpose"] == "Test trip"
    assert data["country"] == "Germany"
    assert data["city"] == "Berlin"
    assert data["full_days"] == 2
    assert data["half_days"] == 1
    assert data["total_days"] == 2.5


def test_per_diem_recalculate(client, user):
    """Test recalculating per diem amount"""
    per_diem = PerDiem(
        user_id=user.id,
        trip_purpose="Trip",
        start_date=date(2025, 10, 20),
        end_date=date(2025, 10, 22),
        country="Germany",
        full_day_rate=28,
        half_day_rate=14,
        full_days=2,
        half_days=0,
    )

    db.session.add(per_diem)
    db.session.commit()

    initial_amount = per_diem.calculated_amount
    assert initial_amount == Decimal("56")

    # Change days
    per_diem.full_days = 3
    new_amount = per_diem.recalculate_amount()

    assert new_amount == Decimal("84")
    assert per_diem.calculated_amount == Decimal("84")


def test_per_diem_create_expense(client, user):
    """Test creating expense from per diem claim"""
    per_diem = PerDiem(
        user_id=user.id,
        trip_purpose="Conference",
        start_date=date(2025, 10, 20),
        end_date=date(2025, 10, 23),
        country="Germany",
        city="Berlin",
        full_day_rate=28,
        half_day_rate=14,
        full_days=3,
        half_days=1,
    )

    db.session.add(per_diem)
    db.session.commit()

    # Create expense
    expense = per_diem.create_expense()

    assert expense is not None
    assert expense.user_id == user.id
    assert expense.category == "meals"
    assert expense.amount == per_diem.calculated_amount
    assert "Berlin, Germany" in expense.title
