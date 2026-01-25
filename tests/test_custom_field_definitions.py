"""
Test suite for Custom Field Definitions.
Tests model creation, deletion, and client field cleanup.
"""

import pytest
from datetime import datetime
from app.models import CustomFieldDefinition, Client, User
from app import db


# ============================================================================
# CustomFieldDefinition Model Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.models
@pytest.mark.smoke
def test_custom_field_definition_creation(app, admin_user):
    """Test basic custom field definition creation."""
    with app.app_context():
        definition = CustomFieldDefinition(
            field_key="debtor_number",
            label="Debtor Number",
            description="Client's debtor number in ERP system",
            is_mandatory=False,
            is_active=True,
            order=1,
            created_by=admin_user.id,
        )
        db.session.add(definition)
        db.session.commit()

        assert definition.id is not None
        assert definition.field_key == "debtor_number"
        assert definition.label == "Debtor Number"
        assert definition.is_mandatory is False
        assert definition.is_active is True
        assert definition.order == 1
        assert definition.created_at is not None
        assert definition.updated_at is not None


@pytest.mark.unit
@pytest.mark.models
def test_count_clients_with_value_no_clients(app, admin_user):
    """Test counting clients with value when no clients have the field."""
    with app.app_context():
        definition = CustomFieldDefinition(
            field_key="test_field",
            label="Test Field",
            created_by=admin_user.id,
        )
        db.session.add(definition)
        db.session.commit()

        count = definition.count_clients_with_value()
        assert count == 0


@pytest.mark.unit
@pytest.mark.models
def test_count_clients_with_value_with_clients(app, admin_user, test_client):
    """Test counting clients with value when clients have the field."""
    with app.app_context():
        definition = CustomFieldDefinition(
            field_key="test_field",
            label="Test Field",
            created_by=admin_user.id,
        )
        db.session.add(definition)
        db.session.commit()

        # Re-query client so it's in the current session
        client = Client.query.get(test_client.id)
        client.set_custom_field("test_field", "test_value")
        db.session.commit()

        count = definition.count_clients_with_value()
        assert count == 1

        # Add another client with the field
        client2 = Client(name="Test Client 2")
        db.session.add(client2)
        client2.set_custom_field("test_field", "another_value")
        db.session.commit()

        count = definition.count_clients_with_value()
        assert count == 2


@pytest.mark.unit
@pytest.mark.models
def test_count_clients_with_value_ignores_empty(app, admin_user, test_client):
    """Test that empty values are not counted."""
    with app.app_context():
        definition = CustomFieldDefinition(
            field_key="test_field",
            label="Test Field",
            created_by=admin_user.id,
        )
        db.session.add(definition)
        db.session.commit()

        # Re-query client so it's in the current session
        client = Client.query.get(test_client.id)
        # Set empty value
        client.set_custom_field("test_field", "")
        db.session.commit()

        count = definition.count_clients_with_value()
        assert count == 0

        # Set whitespace-only value
        client.set_custom_field("test_field", "   ")
        db.session.commit()

        count = definition.count_clients_with_value()
        assert count == 0

        # Set actual value
        client.set_custom_field("test_field", "valid_value")
        db.session.commit()

        count = definition.count_clients_with_value()
        assert count == 1


@pytest.mark.unit
@pytest.mark.models
def test_count_clients_with_value_ignores_other_fields(app, admin_user, test_client):
    """Test that only the specific field is counted."""
    with app.app_context():
        definition = CustomFieldDefinition(
            field_key="test_field",
            label="Test Field",
            created_by=admin_user.id,
        )
        db.session.add(definition)
        db.session.commit()

        # Re-query client so it's in the current session
        client = Client.query.get(test_client.id)
        # Set a different field
        client.set_custom_field("other_field", "value")
        db.session.commit()

        count = definition.count_clients_with_value()
        assert count == 0

        # Set the correct field
        client.set_custom_field("test_field", "value")
        db.session.commit()

        count = definition.count_clients_with_value()
        assert count == 1


# ============================================================================
# Custom Field Definition Deletion Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.database
def test_delete_custom_field_removes_from_clients(app, admin_user, test_client, admin_authenticated_client):
    """Test that deleting a custom field definition removes it from all clients."""
    with app.app_context():
        # Create custom field definition
        definition = CustomFieldDefinition(
            field_key="debtor_number",
            label="Debtor Number",
            created_by=admin_user.id,
        )
        db.session.add(definition)
        db.session.commit()

        # Set custom field value for client
        test_client.set_custom_field("debtor_number", "12345")
        db.session.commit()

        # Verify client has the field
        assert test_client.get_custom_field("debtor_number") == "12345"

        # Delete the definition via route
        response = admin_authenticated_client.post(
            f"/admin/custom-field-definitions/{definition.id}/delete",
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify definition is deleted
        deleted_definition = CustomFieldDefinition.query.get(definition.id)
        assert deleted_definition is None

        # Verify field is removed from client (re-query; test_client may be detached after request)
        client_after = Client.query.get(test_client.id)
        assert client_after.get_custom_field("debtor_number") is None
        assert "debtor_number" not in (client_after.custom_fields or {})


@pytest.mark.integration
@pytest.mark.database
def test_delete_custom_field_multiple_clients(app, admin_user, test_client, admin_authenticated_client):
    """Test that deleting a custom field removes it from multiple clients."""
    with app.app_context():
        # Create custom field definition
        definition = CustomFieldDefinition(
            field_key="erp_id",
            label="ERP ID",
            created_by=admin_user.id,
        )
        db.session.add(definition)
        db.session.commit()

        # Create multiple clients with the field
        client1 = Client(name="Client 1")
        client2 = Client(name="Client 2")
        client3 = Client(name="Client 3")
        db.session.add_all([client1, client2, client3])
        client1.set_custom_field("erp_id", "ERP001")
        client2.set_custom_field("erp_id", "ERP002")
        client3.set_custom_field("erp_id", "ERP003")
        db.session.commit()

        # Delete the definition
        response = admin_authenticated_client.post(
            f"/admin/custom-field-definitions/{definition.id}/delete",
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify field is removed from all clients
        db.session.refresh(client1)
        db.session.refresh(client2)
        db.session.refresh(client3)

        assert client1.get_custom_field("erp_id") is None
        assert client2.get_custom_field("erp_id") is None
        assert client3.get_custom_field("erp_id") is None


@pytest.mark.integration
@pytest.mark.database
def test_delete_custom_field_no_clients_affected(app, admin_user, admin_authenticated_client):
    """Test deleting a custom field when no clients have values."""
    with app.app_context():
        # Create custom field definition
        definition = CustomFieldDefinition(
            field_key="unused_field",
            label="Unused Field",
            created_by=admin_user.id,
        )
        db.session.add(definition)
        db.session.commit()

        # Delete the definition
        response = admin_authenticated_client.post(
            f"/admin/custom-field-definitions/{definition.id}/delete",
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify definition is deleted
        deleted_definition = CustomFieldDefinition.query.get(definition.id)
        assert deleted_definition is None


@pytest.mark.integration
@pytest.mark.database
def test_delete_custom_field_preserves_other_fields(app, admin_user, test_client, admin_authenticated_client):
    """Test that deleting one custom field doesn't affect other custom fields."""
    with app.app_context():
        # Create two custom field definitions
        definition1 = CustomFieldDefinition(
            field_key="field1",
            label="Field 1",
            created_by=admin_user.id,
        )
        definition2 = CustomFieldDefinition(
            field_key="field2",
            label="Field 2",
            created_by=admin_user.id,
        )
        db.session.add_all([definition1, definition2])
        db.session.commit()

        # Set both fields for client
        test_client.set_custom_field("field1", "value1")
        test_client.set_custom_field("field2", "value2")
        db.session.commit()

        # Delete only definition1
        response = admin_authenticated_client.post(
            f"/admin/custom-field-definitions/{definition1.id}/delete",
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify field1 is removed but field2 remains (re-query; test_client may be detached after request)
        client_after = Client.query.get(test_client.id)
        assert client_after.get_custom_field("field1") is None
        assert client_after.get_custom_field("field2") == "value2"

