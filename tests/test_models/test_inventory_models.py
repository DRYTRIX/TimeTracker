"""Tests for inventory management models"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from app import db
from app.models import (
    Warehouse, StockItem, WarehouseStock, StockMovement, StockReservation,
    ProjectStockAllocation, User, Project
)


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(username='testuser', role='admin')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_warehouse(db_session, test_user):
    """Create a test warehouse"""
    warehouse = Warehouse(
        name='Main Warehouse',
        code='WH-001',
        created_by=test_user.id
    )
    db_session.add(warehouse)
    db_session.commit()
    return warehouse


@pytest.fixture
def test_stock_item(db_session, test_user):
    """Create a test stock item"""
    item = StockItem(
        sku='TEST-001',
        name='Test Product',
        created_by=test_user.id,
        default_price=Decimal('10.00'),
        default_cost=Decimal('5.00'),
        is_trackable=True,
        reorder_point=Decimal('10.00')
    )
    db_session.add(item)
    db_session.commit()
    return item


class TestWarehouse:
    """Test Warehouse model"""
    
    def test_create_warehouse(self, db_session, test_user):
        """Test creating a warehouse"""
        warehouse = Warehouse(
            name='Test Warehouse',
            code='WH-TEST',
            created_by=test_user.id,
            address='123 Test St',
            contact_person='John Doe',
            contact_email='john@test.com'
        )
        db_session.add(warehouse)
        db_session.commit()
        
        assert warehouse.id is not None
        assert warehouse.name == 'Test Warehouse'
        assert warehouse.code == 'WH-TEST'
        assert warehouse.is_active is True
    
    def test_warehouse_code_uppercase(self, db_session, test_user):
        """Test that warehouse code is automatically uppercased"""
        warehouse = Warehouse(
            name='Test',
            code='wh-test',
            created_by=test_user.id
        )
        assert warehouse.code == 'WH-TEST'
    
    def test_warehouse_to_dict(self, db_session, test_user):
        """Test warehouse to_dict method"""
        warehouse = Warehouse(
            name='Test Warehouse',
            code='WH-TEST',
            created_by=test_user.id
        )
        db_session.add(warehouse)
        db_session.commit()
        
        data = warehouse.to_dict()
        assert data['name'] == 'Test Warehouse'
        assert data['code'] == 'WH-TEST'
        assert 'created_at' in data


class TestStockItem:
    """Test StockItem model"""
    
    def test_create_stock_item(self, db_session, test_user):
        """Test creating a stock item"""
        item = StockItem(
            sku='PROD-001',
            name='Test Product',
            created_by=test_user.id,
            default_price=Decimal('25.50'),
            default_cost=Decimal('15.00')
        )
        db_session.add(item)
        db_session.commit()
        
        assert item.id is not None
        assert item.sku == 'PROD-001'
        assert item.name == 'Test Product'
        assert item.is_active is True
        assert item.is_trackable is True
    
    def test_sku_uppercase(self, db_session, test_user):
        """Test that SKU is automatically uppercased"""
        item = StockItem(
            sku='prod-001',
            name='Test',
            created_by=test_user.id
        )
        assert item.sku == 'PROD-001'
    
    def test_total_quantity_on_hand(self, db_session, test_user, test_stock_item, test_warehouse):
        """Test calculating total quantity on hand"""
        # Create stock in warehouse
        stock = WarehouseStock(
            warehouse_id=test_warehouse.id,
            stock_item_id=test_stock_item.id,
            quantity_on_hand=Decimal('50.00')
        )
        db_session.add(stock)
        db_session.commit()
        
        # Refresh item to get updated quantities
        db_session.refresh(test_stock_item)
        
        assert test_stock_item.total_quantity_on_hand == Decimal('50.00')
    
    def test_is_low_stock(self, db_session, test_user, test_stock_item, test_warehouse):
        """Test low stock detection"""
        # Create stock below reorder point
        stock = WarehouseStock(
            warehouse_id=test_warehouse.id,
            stock_item_id=test_stock_item.id,
            quantity_on_hand=Decimal('5.00')  # Below reorder_point of 10
        )
        db_session.add(stock)
        db_session.commit()
        
        db_session.refresh(test_stock_item)
        assert test_stock_item.is_low_stock is True
        
        # Increase stock above reorder point
        stock.quantity_on_hand = Decimal('15.00')
        db_session.commit()
        db_session.refresh(test_stock_item)
        assert test_stock_item.is_low_stock is False


class TestWarehouseStock:
    """Test WarehouseStock model"""
    
    def test_create_warehouse_stock(self, db_session, test_stock_item, test_warehouse):
        """Test creating warehouse stock"""
        stock = WarehouseStock(
            warehouse_id=test_warehouse.id,
            stock_item_id=test_stock_item.id,
            quantity_on_hand=Decimal('100.00'),
            quantity_reserved=Decimal('10.00')
        )
        db_session.add(stock)
        db_session.commit()
        
        assert stock.id is not None
        assert stock.quantity_on_hand == Decimal('100.00')
        assert stock.quantity_reserved == Decimal('10.00')
        assert stock.quantity_available == Decimal('90.00')
    
    def test_reserve_quantity(self, db_session, test_stock_item, test_warehouse):
        """Test reserving quantity"""
        stock = WarehouseStock(
            warehouse_id=test_warehouse.id,
            stock_item_id=test_stock_item.id,
            quantity_on_hand=Decimal('100.00')
        )
        db_session.add(stock)
        db_session.commit()
        
        stock.reserve(Decimal('20.00'))
        db_session.commit()
        
        assert stock.quantity_reserved == Decimal('20.00')
        assert stock.quantity_available == Decimal('80.00')
    
    def test_reserve_insufficient_stock(self, db_session, test_stock_item, test_warehouse):
        """Test that reserving more than available raises error"""
        stock = WarehouseStock(
            warehouse_id=test_warehouse.id,
            stock_item_id=test_stock_item.id,
            quantity_on_hand=Decimal('100.00'),
            quantity_reserved=Decimal('90.00')
        )
        db_session.add(stock)
        db_session.commit()
        
        with pytest.raises(ValueError, match='Insufficient stock'):
            stock.reserve(Decimal('20.00'))  # Only 10 available
    
    def test_release_reservation(self, db_session, test_stock_item, test_warehouse):
        """Test releasing reserved quantity"""
        stock = WarehouseStock(
            warehouse_id=test_warehouse.id,
            stock_item_id=test_stock_item.id,
            quantity_on_hand=Decimal('100.00'),
            quantity_reserved=Decimal('30.00')
        )
        db_session.add(stock)
        db_session.commit()
        
        stock.release_reservation(Decimal('10.00'))
        db_session.commit()
        
        assert stock.quantity_reserved == Decimal('20.00')
        assert stock.quantity_available == Decimal('80.00')
    
    def test_adjust_on_hand(self, db_session, test_stock_item, test_warehouse):
        """Test adjusting on-hand quantity"""
        stock = WarehouseStock(
            warehouse_id=test_warehouse.id,
            stock_item_id=test_stock_item.id,
            quantity_on_hand=Decimal('100.00')
        )
        db_session.add(stock)
        db_session.commit()
        
        stock.adjust_on_hand(Decimal('25.00'))  # Add
        db_session.commit()
        assert stock.quantity_on_hand == Decimal('125.00')
        
        stock.adjust_on_hand(Decimal('-50.00'))  # Remove
        db_session.commit()
        assert stock.quantity_on_hand == Decimal('75.00')


class TestStockMovement:
    """Test StockMovement model"""
    
    def test_record_movement(self, db_session, test_user, test_stock_item, test_warehouse):
        """Test recording a stock movement"""
        movement, updated_stock = StockMovement.record_movement(
            movement_type='adjustment',
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
            quantity=Decimal('50.00'),
            moved_by=test_user.id,
            reason='Initial stock',
            update_stock=True
        )
        db_session.commit()
        
        assert movement.id is not None
        assert movement.quantity == Decimal('50.00')
        assert updated_stock is not None
        assert updated_stock.quantity_on_hand == Decimal('50.00')
    
    def test_movement_updates_stock(self, db_session, test_user, test_stock_item, test_warehouse):
        """Test that movement updates warehouse stock"""
        # Create initial stock
        stock = WarehouseStock(
            warehouse_id=test_warehouse.id,
            stock_item_id=test_stock_item.id,
            quantity_on_hand=Decimal('100.00')
        )
        db_session.add(stock)
        db_session.commit()
        
        # Record removal
        movement, updated_stock = StockMovement.record_movement(
            movement_type='sale',
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
            quantity=Decimal('-25.00'),
            moved_by=test_user.id,
            update_stock=True
        )
        db_session.commit()
        
        assert updated_stock.quantity_on_hand == Decimal('75.00')


class TestStockReservation:
    """Test StockReservation model"""
    
    def test_create_reservation(self, db_session, test_user, test_stock_item, test_warehouse):
        """Test creating a stock reservation"""
        # Create stock first
        stock = WarehouseStock(
            warehouse_id=test_warehouse.id,
            stock_item_id=test_stock_item.id,
            quantity_on_hand=Decimal('100.00')
        )
        db_session.add(stock)
        db_session.commit()
        
        reservation, updated_stock = StockReservation.create_reservation(
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
            quantity=Decimal('20.00'),
            reservation_type='quote',
            reservation_id=1,
            reserved_by=test_user.id,
            expires_in_days=30
        )
        db_session.commit()
        
        assert reservation.id is not None
        assert reservation.status == 'reserved'
        assert updated_stock.quantity_reserved == Decimal('20.00')
        assert updated_stock.quantity_available == Decimal('80.00')
    
    def test_reservation_insufficient_stock(self, db_session, test_user, test_stock_item, test_warehouse):
        """Test that creating reservation with insufficient stock raises error"""
        stock = WarehouseStock(
            warehouse_id=test_warehouse.id,
            stock_item_id=test_stock_item.id,
            quantity_on_hand=Decimal('10.00')
        )
        db_session.add(stock)
        db_session.commit()
        
        with pytest.raises(ValueError, match='Insufficient stock'):
            StockReservation.create_reservation(
                stock_item_id=test_stock_item.id,
                warehouse_id=test_warehouse.id,
                quantity=Decimal('20.00'),
                reservation_type='quote',
                reservation_id=1,
                reserved_by=test_user.id
            )
    
    def test_fulfill_reservation(self, db_session, test_user, test_stock_item, test_warehouse):
        """Test fulfilling a reservation"""
        stock = WarehouseStock(
            warehouse_id=test_warehouse.id,
            stock_item_id=test_stock_item.id,
            quantity_on_hand=Decimal('100.00'),
            quantity_reserved=Decimal('20.00')
        )
        db_session.add(stock)
        db_session.commit()
        
        reservation = StockReservation(
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
            quantity=Decimal('20.00'),
            reservation_type='quote',
            reservation_id=1,
            reserved_by=test_user.id
        )
        db_session.add(reservation)
        db_session.commit()
        
        reservation.fulfill()
        db_session.commit()
        
        assert reservation.status == 'fulfilled'
        assert reservation.fulfilled_at is not None
        db_session.refresh(stock)
        assert stock.quantity_reserved == Decimal('0.00')
    
    def test_cancel_reservation(self, db_session, test_user, test_stock_item, test_warehouse):
        """Test cancelling a reservation"""
        stock = WarehouseStock(
            warehouse_id=test_warehouse.id,
            stock_item_id=test_stock_item.id,
            quantity_on_hand=Decimal('100.00'),
            quantity_reserved=Decimal('20.00')
        )
        db_session.add(stock)
        db_session.commit()
        
        reservation = StockReservation(
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
            quantity=Decimal('20.00'),
            reservation_type='quote',
            reservation_id=1,
            reserved_by=test_user.id
        )
        db_session.add(reservation)
        db_session.commit()
        
        reservation.cancel()
        db_session.commit()
        
        assert reservation.status == 'cancelled'
        assert reservation.cancelled_at is not None
        db_session.refresh(stock)
        assert stock.quantity_reserved == Decimal('0.00')
    
    def test_expired_reservation(self, db_session, test_user, test_stock_item, test_warehouse):
        """Test expired reservation detection"""
        reservation = StockReservation(
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
            quantity=Decimal('10.00'),
            reservation_type='quote',
            reservation_id=1,
            reserved_by=test_user.id,
            expires_at=datetime.utcnow() - timedelta(days=1)  # Expired yesterday
        )
        db_session.add(reservation)
        db_session.commit()
        
        assert reservation.is_expired is True


class TestProjectStockAllocation:
    """Test ProjectStockAllocation model"""
    
    def test_create_allocation(self, db_session, test_user, test_stock_item, test_warehouse):
        """Test creating a project stock allocation"""
        project = Project(
            name='Test Project',
            client_id=1,  # Assuming client exists
            billable=True
        )
        db_session.add(project)
        db_session.commit()
        
        allocation = ProjectStockAllocation(
            project_id=project.id,
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
            quantity_allocated=Decimal('50.00'),
            allocated_by=test_user.id
        )
        db_session.add(allocation)
        db_session.commit()
        
        assert allocation.id is not None
        assert allocation.quantity_allocated == Decimal('50.00')
        assert allocation.quantity_used == Decimal('0.00')
        assert allocation.quantity_remaining == Decimal('50.00')
    
    def test_record_usage(self, db_session, test_user, test_stock_item, test_warehouse):
        """Test recording usage of allocated stock"""
        project = Project(
            name='Test Project',
            client_id=1,
            billable=True
        )
        db_session.add(project)
        db_session.commit()
        
        allocation = ProjectStockAllocation(
            project_id=project.id,
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
            quantity_allocated=Decimal('50.00'),
            allocated_by=test_user.id
        )
        db_session.add(allocation)
        db_session.commit()
        
        allocation.record_usage(Decimal('15.00'))
        db_session.commit()
        
        assert allocation.quantity_used == Decimal('15.00')
        assert allocation.quantity_remaining == Decimal('35.00')
    
    def test_record_usage_exceeds_allocation(self, db_session, test_user, test_stock_item, test_warehouse):
        """Test that using more than allocated raises error"""
        project = Project(
            name='Test Project',
            client_id=1,
            billable=True
        )
        db_session.add(project)
        db_session.commit()
        
        allocation = ProjectStockAllocation(
            project_id=project.id,
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
            quantity_allocated=Decimal('50.00'),
            allocated_by=test_user.id
        )
        db_session.add(allocation)
        db_session.commit()
        
        with pytest.raises(ValueError, match='Cannot use more than allocated'):
            allocation.record_usage(Decimal('60.00'))

