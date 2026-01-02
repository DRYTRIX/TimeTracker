"""Tests for supplier routes"""

import pytest
from flask import url_for
from app import db
from app.models import Supplier, User


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(username="testuser", role="admin")
    user.set_password("testpass")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_supplier(db_session, test_user):
    """Create a test supplier"""
    supplier = Supplier(code="SUP-001", name="Test Supplier", created_by=test_user.id)
    db_session.add(supplier)
    db_session.commit()
    return supplier


class TestSupplierRoutes:
    """Test supplier routes"""

    def test_list_suppliers(self, client, test_user, test_supplier):
        """Test listing suppliers"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get(url_for("inventory.list_suppliers"))
        assert response.status_code == 200
        assert b"Suppliers" in response.data
        assert b"SUP-001" in response.data

    def test_create_supplier(self, client, test_user):
        """Test creating a supplier"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.new_supplier"),
            data={
                "code": "SUP-NEW",
                "name": "New Supplier",
                "email": "new@supplier.com",
                "is_active": "on",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Check if supplier was created
        supplier = Supplier.query.filter_by(code="SUP-NEW").first()
        assert supplier is not None
        assert supplier.name == "New Supplier"

    def test_create_supplier_duplicate_code(self, client, test_user, test_supplier):
        """Test creating supplier with duplicate code"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.new_supplier"),
            data={
                "code": test_supplier.code,  # Duplicate code
                "name": "Another Supplier",
                "is_active": "on",
            },
            follow_redirects=True,
        )

        # Should show error message
        assert response.status_code == 200
        assert b"already exists" in response.data.lower() or b"duplicate" in response.data.lower()

    def test_view_supplier(self, client, test_user, test_supplier):
        """Test viewing supplier details"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get(url_for("inventory.view_supplier", supplier_id=test_supplier.id))
        assert response.status_code == 200
        assert b"SUP-001" in response.data
        assert b"Test Supplier" in response.data

    def test_edit_supplier(self, client, test_user, test_supplier):
        """Test editing supplier"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.edit_supplier", supplier_id=test_supplier.id),
            data={
                "code": test_supplier.code,
                "name": "Updated Supplier",
                "email": "updated@supplier.com",
                "is_active": "on",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Check if supplier was updated
        db.session.refresh(test_supplier)
        assert test_supplier.name == "Updated Supplier"

    def test_delete_supplier(self, client, test_user, test_supplier):
        """Test deleting (deactivating) supplier"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            url_for("inventory.delete_supplier", supplier_id=test_supplier.id),
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Check if supplier was deactivated
        db.session.refresh(test_supplier)
        assert test_supplier.is_active is False
