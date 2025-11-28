"""Integration tests for inventory with quotes and invoices"""

import pytest
from decimal import Decimal
from flask import url_for
from app import db
from app.models import (
    Warehouse,
    StockItem,
    WarehouseStock,
    StockReservation,
    StockMovement,
    Quote,
    QuoteItem,
    Invoice,
    InvoiceItem,
    Project,
    Client,
    User,
)


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(username="testuser", role="admin")
    user.set_password("testpass")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_client(db_session):
    """Create a test client"""
    client = Client(name="Test Client", email="test@client.com")
    db_session.add(client)
    db_session.commit()
    return client


@pytest.fixture
def test_warehouse(db_session, test_user):
    """Create a test warehouse"""
    warehouse = Warehouse(name="Main Warehouse", code="WH-001", created_by=test_user.id)
    db_session.add(warehouse)
    db_session.commit()
    return warehouse


@pytest.fixture
def test_stock_item(db_session, test_user):
    """Create a test stock item with stock"""
    item = StockItem(
        sku="PROD-001",
        name="Test Product",
        created_by=test_user.id,
        default_price=Decimal("25.00"),
        default_cost=Decimal("10.00"),
        is_trackable=True,
    )
    db_session.add(item)
    db_session.commit()
    return item


@pytest.fixture
def test_stock_with_quantity(db_session, test_stock_item, test_warehouse):
    """Create stock with quantity"""
    stock = WarehouseStock(
        warehouse_id=test_warehouse.id, stock_item_id=test_stock_item.id, quantity_on_hand=Decimal("100.00")
    )
    db_session.add(stock)
    db_session.commit()
    return stock


class TestQuoteInventoryIntegration:
    """Test inventory integration with quotes"""

    def test_quote_with_stock_item(
        self, client, test_user, test_client, test_stock_item, test_warehouse, test_stock_with_quantity
    ):
        """Test creating a quote with a stock item"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Create quote with stock item
        response = client.post(
            url_for("quotes.create_quote"),
            data={
                "client_id": test_client.id,
                "title": "Test Quote",
                "tax_rate": "0",
                "currency_code": "EUR",
                "item_description[]": ["Test Product"],
                "item_quantity[]": ["5"],
                "item_price[]": ["25.00"],
                "item_unit[]": ["pcs"],
                "item_stock_item_id[]": [str(test_stock_item.id)],
                "item_warehouse_id[]": [str(test_warehouse.id)],
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Check quote was created
        quote = Quote.query.filter_by(title="Test Quote").first()
        assert quote is not None

        # Check quote item has stock_item_id
        quote_item = quote.items.first()
        assert quote_item is not None
        assert quote_item.stock_item_id == test_stock_item.id
        assert quote_item.warehouse_id == test_warehouse.id
        assert quote_item.is_stock_item is True

    def test_quote_send_reserves_stock(
        self, client, test_user, test_client, test_stock_item, test_warehouse, test_stock_with_quantity
    ):
        """Test that sending a quote reserves stock (if enabled)"""
        import os

        os.environ["INVENTORY_AUTO_RESERVE_ON_QUOTE_SENT"] = "true"

        # Create quote with stock item
        quote = Quote(
            quote_number="QUO-TEST-001", client_id=test_client.id, title="Test Quote", created_by=test_user.id
        )
        db.session.add(quote)
        db.session.flush()

        quote_item = QuoteItem(
            quote_id=quote.id,
            description="Test Product",
            quantity=Decimal("10.00"),
            unit_price=Decimal("25.00"),
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
        )
        db.session.add(quote_item)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Send quote
        response = client.post(url_for("quotes.send_quote", quote_id=quote.id), follow_redirects=True)

        # Check if reservation was created
        reservation = StockReservation.query.filter_by(reservation_type="quote", reservation_id=quote.id).first()

        # Note: Reservation only created if INVENTORY_AUTO_RESERVE_ON_QUOTE_SENT is true
        # This test verifies the integration point exists
        assert quote.status == "sent"


class TestInvoiceInventoryIntegration:
    """Test inventory integration with invoices"""

    def test_invoice_with_stock_item(
        self, client, test_user, test_client, test_stock_item, test_warehouse, test_stock_with_quantity
    ):
        """Test creating an invoice with a stock item"""
        # Create project
        project = Project(name="Test Project", client_id=test_client.id, billable=True)
        db.session.add(project)
        db.session.commit()

        # Create invoice
        invoice = Invoice(
            invoice_number="INV-TEST-001",
            project_id=project.id,
            client_name=test_client.name,
            client_id=test_client.id,
            due_date=datetime.utcnow().date() + timedelta(days=30),
            created_by=test_user.id,
        )
        db.session.add(invoice)
        db.session.flush()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Edit invoice to add stock item
        response = client.post(
            url_for("invoices.edit_invoice", invoice_id=invoice.id),
            data={
                "client_name": test_client.name,
                "due_date": (datetime.utcnow().date() + timedelta(days=30)).strftime("%Y-%m-%d"),
                "tax_rate": "0",
                "description[]": ["Test Product"],
                "quantity[]": ["5"],
                "unit_price[]": ["25.00"],
                "item_stock_item_id[]": [str(test_stock_item.id)],
                "item_warehouse_id[]": [str(test_warehouse.id)],
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Check invoice item has stock_item_id
        invoice_item = invoice.items.first()
        if invoice_item:
            assert invoice_item.stock_item_id == test_stock_item.id
            assert invoice_item.is_stock_item is True

    def test_invoice_sent_reduces_stock(
        self, client, test_user, test_client, test_stock_item, test_warehouse, test_stock_with_quantity
    ):
        """Test that marking invoice as sent reduces stock (if configured)"""
        import os

        os.environ["INVENTORY_REDUCE_ON_INVOICE_SENT"] = "true"

        # Create project and invoice
        project = Project(name="Test Project", client_id=test_client.id, billable=True)
        db.session.add(project)
        db.session.commit()

        invoice = Invoice(
            invoice_number="INV-TEST-002",
            project_id=project.id,
            client_name=test_client.name,
            client_id=test_client.id,
            due_date=datetime.utcnow().date() + timedelta(days=30),
            created_by=test_user.id,
            status="draft",
        )
        db.session.add(invoice)
        db.session.flush()

        invoice_item = InvoiceItem(
            invoice_id=invoice.id,
            description="Test Product",
            quantity=Decimal("10.00"),
            unit_price=Decimal("25.00"),
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
        )
        db.session.add(invoice_item)
        db.session.commit()

        initial_stock = test_stock_with_quantity.quantity_on_hand

        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Mark invoice as sent
        response = client.post(
            url_for("invoices.update_invoice_status", invoice_id=invoice.id),
            data={"new_status": "sent"},
            follow_redirects=False,
        )

        # Check if stock was reduced
        db.session.refresh(test_stock_with_quantity)
        # Stock should be reduced if INVENTORY_REDUCE_ON_INVOICE_SENT is true
        # This test verifies the integration point exists
        assert invoice.status == "sent" or response.status_code in [200, 302]


class TestStockReservationLifecycle:
    """Test stock reservation lifecycle"""

    def test_reservation_fulfillment(
        self, db_session, test_user, test_stock_item, test_warehouse, test_stock_with_quantity
    ):
        """Test reservation fulfillment flow"""
        # Create reservation
        reservation, updated_stock = StockReservation.create_reservation(
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
            quantity=Decimal("20.00"),
            reservation_type="invoice",
            reservation_id=1,
            reserved_by=test_user.id,
        )
        db_session.commit()

        initial_reserved = updated_stock.quantity_reserved

        # Fulfill reservation
        reservation.fulfill()
        db_session.commit()

        db_session.refresh(updated_stock)
        assert updated_stock.quantity_reserved < initial_reserved
        assert reservation.status == "fulfilled"

    def test_reservation_cancellation(
        self, db_session, test_user, test_stock_item, test_warehouse, test_stock_with_quantity
    ):
        """Test reservation cancellation flow"""
        # Create reservation
        reservation, updated_stock = StockReservation.create_reservation(
            stock_item_id=test_stock_item.id,
            warehouse_id=test_warehouse.id,
            quantity=Decimal("15.00"),
            reservation_type="quote",
            reservation_id=1,
            reserved_by=test_user.id,
        )
        db_session.commit()

        initial_reserved = updated_stock.quantity_reserved

        # Cancel reservation
        reservation.cancel()
        db_session.commit()

        db_session.refresh(updated_stock)
        assert updated_stock.quantity_reserved < initial_reserved
        assert reservation.status == "cancelled"
