"""
Tests for Mileage model
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from app import db
from app.models import Mileage, User, Project, Client, Expense


@pytest.fixture
def user(client):
    """Create a test user"""
    user = User(username='testuser', email='test@example.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def project(client):
    """Create a test project"""
    client_obj = Client(name='Test Client', company='Test Client')
    db.session.add(client_obj)
    db.session.commit()
    
    project = Project(
        name='Test Project',
        client_id=client_obj.id,
        billable=True
    )
    db.session.add(project)
    db.session.commit()
    return project


def test_create_mileage(client, user):
    """Test creating a mileage entry"""
    mileage = Mileage(
        user_id=user.id,
        trip_date=date.today(),
        purpose='Client meeting',
        start_location='Office',
        end_location='Client Site',
        distance_km=45.5,
        rate_per_km=0.30,
        vehicle_type='car'
    )
    
    db.session.add(mileage)
    db.session.commit()
    
    assert mileage.id is not None
    assert mileage.purpose == 'Client meeting'
    assert mileage.distance_km == Decimal('45.5')
    assert mileage.rate_per_km == Decimal('0.30')
    assert mileage.calculated_amount == Decimal('13.65')
    assert mileage.status == 'pending'


def test_mileage_round_trip(client, user):
    """Test mileage calculation for round trip"""
    mileage = Mileage(
        user_id=user.id,
        trip_date=date.today(),
        purpose='Round trip',
        start_location='A',
        end_location='B',
        distance_km=50,
        rate_per_km=0.30,
        is_round_trip=True
    )
    
    db.session.add(mileage)
    db.session.commit()
    
    # Check that total distance and amount are doubled
    assert mileage.total_distance_km == 100.0
    assert mileage.total_amount == 30.0  # 50 km * 2 * 0.30


def test_mileage_approval(client, user):
    """Test mileage approval workflow"""
    admin = User(username='admin', email='admin@example.com', role='admin')
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    
    mileage = Mileage(
        user_id=user.id,
        trip_date=date.today(),
        purpose='Test trip',
        start_location='A',
        end_location='B',
        distance_km=30,
        rate_per_km=0.30
    )
    
    db.session.add(mileage)
    db.session.commit()
    
    # Approve mileage
    mileage.approve(admin.id, notes='Approved')
    db.session.commit()
    
    assert mileage.status == 'approved'
    assert mileage.approved_by == admin.id
    assert mileage.approved_at is not None
    assert 'Approved' in mileage.notes


def test_mileage_rejection(client, user):
    """Test mileage rejection workflow"""
    admin = User(username='admin', email='admin@example.com', role='admin')
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    
    mileage = Mileage(
        user_id=user.id,
        trip_date=date.today(),
        purpose='Test trip',
        start_location='A',
        end_location='B',
        distance_km=30,
        rate_per_km=0.30
    )
    
    db.session.add(mileage)
    db.session.commit()
    
    # Reject mileage
    mileage.reject(admin.id, reason='Missing documentation')
    db.session.commit()
    
    assert mileage.status == 'rejected'
    assert mileage.approved_by == admin.id
    assert mileage.rejection_reason == 'Missing documentation'


def test_mileage_create_expense(client, user, project):
    """Test creating expense from mileage entry"""
    mileage = Mileage(
        user_id=user.id,
        trip_date=date.today(),
        purpose='Client visit',
        start_location='Office',
        end_location='Client',
        distance_km=40,
        rate_per_km=0.30,
        project_id=project.id,
        is_round_trip=True
    )
    
    db.session.add(mileage)
    db.session.commit()
    
    # Create expense
    expense = mileage.create_expense()
    
    assert expense is not None
    assert expense.user_id == user.id
    assert expense.category == 'travel'
    assert expense.amount == mileage.total_amount
    assert expense.project_id == project.id
    assert 'Distance' in expense.description


def test_mileage_to_dict(client, user):
    """Test converting mileage to dictionary"""
    mileage = Mileage(
        user_id=user.id,
        trip_date=date.today(),
        purpose='Test trip',
        start_location='A',
        end_location='B',
        distance_km=25.5,
        rate_per_km=0.30
    )
    
    db.session.add(mileage)
    db.session.commit()
    
    data = mileage.to_dict()
    
    assert data['id'] == mileage.id
    assert data['user_id'] == user.id
    assert data['purpose'] == 'Test trip'
    assert data['start_location'] == 'A'
    assert data['end_location'] == 'B'
    assert data['distance_km'] == 25.5
    assert data['rate_per_km'] == 0.30
    assert data['calculated_amount'] == 7.65
    assert data['status'] == 'pending'


def test_get_total_distance(client, user):
    """Test getting total distance traveled"""
    today = date.today()
    
    # Create multiple mileage entries
    mileage1 = Mileage(
        user_id=user.id,
        trip_date=today,
        purpose='Trip 1',
        start_location='A',
        end_location='B',
        distance_km=30,
        rate_per_km=0.30,
        status='approved'
    )
    
    mileage2 = Mileage(
        user_id=user.id,
        trip_date=today,
        purpose='Trip 2',
        start_location='C',
        end_location='D',
        distance_km=50,
        rate_per_km=0.30,
        status='approved'
    )
    
    db.session.add_all([mileage1, mileage2])
    db.session.commit()
    
    # Get total distance
    total = Mileage.get_total_distance(user_id=user.id)
    
    assert total == 80.0


def test_mileage_default_rates(client):
    """Test getting default mileage rates"""
    rates = Mileage.get_default_rates()
    
    assert 'car' in rates
    assert 'motorcycle' in rates
    assert 'van' in rates
    assert 'truck' in rates
    
    assert rates['car']['km'] == 0.30
    assert rates['motorcycle']['km'] == 0.20


def test_mileage_reimbursement(client, user):
    """Test marking mileage as reimbursed"""
    admin = User(username='admin', email='admin@example.com', role='admin')
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    
    mileage = Mileage(
        user_id=user.id,
        trip_date=date.today(),
        purpose='Test trip',
        start_location='A',
        end_location='B',
        distance_km=30,
        rate_per_km=0.30,
        status='approved'
    )
    
    db.session.add(mileage)
    db.session.commit()
    
    # Mark as reimbursed
    mileage.mark_as_reimbursed()
    db.session.commit()
    
    assert mileage.status == 'reimbursed'
    assert mileage.reimbursed is True
    assert mileage.reimbursed_at is not None

