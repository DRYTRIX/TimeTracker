"""Custom field definitions are filtered by entity_type for forms."""

import pytest

from app import db
from app.models import CustomFieldDefinition, User


@pytest.mark.unit
def test_get_active_definitions_filters_by_entity_type(app, admin_user):
    with app.app_context():
        creator = db.session.get(User, admin_user.id)
        client_field = CustomFieldDefinition(
            field_key="client_only_code",
            label="Client code",
            entity_type="client",
            is_active=True,
            created_by=creator.id,
        )
        project_field = CustomFieldDefinition(
            field_key="project_only_code",
            label="Project code",
            entity_type="project",
            is_active=True,
            created_by=creator.id,
        )
        db.session.add_all([client_field, project_field])
        db.session.commit()

        client_defs = CustomFieldDefinition.get_active_definitions("client")
        keys = {d.field_key for d in client_defs}
        assert "client_only_code" in keys
        assert "project_only_code" not in keys

        project_defs = CustomFieldDefinition.get_active_definitions("project")
        pkeys = {d.field_key for d in project_defs}
        assert "project_only_code" in pkeys
        assert "client_only_code" not in pkeys
