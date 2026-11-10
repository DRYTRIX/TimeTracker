"""Service helpers for global custom field definitions and entity values."""

from typing import Any, Dict, List, Optional, Union

from sqlalchemy.exc import ProgrammingError


class CustomFieldService:
    """Read definitions and apply custom field values to entities."""

    def get_definitions(self, entity_type: str) -> List[Any]:
        """Return active custom field definitions for the given entity type."""
        from app.models import CustomFieldDefinition

        entity_type = (entity_type or "client").strip().lower()
        try:
            return (
                CustomFieldDefinition.query.filter_by(is_active=True, entity_type=entity_type)
                .order_by(CustomFieldDefinition.order, CustomFieldDefinition.label)
                .all()
            )
        except ProgrammingError as e:
            if "does not exist" in str(e.orig) or "relation" in str(e.orig).lower():
                try:
                    from flask import current_app

                    if current_app:
                        current_app.logger.warning(
                            "custom_field_definitions table does not exist. Run migration: flask db upgrade"
                        )
                except RuntimeError:
                    pass
                return []
            raise
        except Exception:
            return []

    def _form_value(self, form_data: Union[Dict[str, Any], Any], field_key: str) -> str:
        name = f"custom_field_{field_key}"
        if hasattr(form_data, "get"):
            raw = form_data.get(name, "")
        else:
            raw = form_data.get(name, "")
        return (raw or "").strip() if isinstance(raw, str) else str(raw).strip()

    def apply_from_form(
        self,
        entity,
        entity_type: str,
        form_data: Union[Dict[str, Any], Any],
        *,
        validate_mandatory: bool = True,
    ) -> Optional[str]:
        """Read ``custom_field_<key>`` from form data into ``entity.custom_fields``. Returns error or None."""
        definitions = self.get_definitions(entity_type)
        if not definitions:
            return None

        collected = {}
        for definition in definitions:
            field_value = self._form_value(form_data, definition.field_key)
            if field_value:
                collected[definition.field_key] = field_value
            elif validate_mandatory and definition.is_mandatory:
                return definition.label

        merged = dict(getattr(entity, "custom_fields", None) or {})
        for definition in definitions:
            key = definition.field_key
            if key in collected:
                merged[key] = collected[key]
            elif key in merged:
                del merged[key]

        entity.custom_fields = merged if merged else {}
        return None

    def apply_from_dict(
        self,
        entity,
        entity_type: str,
        payload: Optional[Dict[str, Any]],
        *,
        merge: bool = True,
    ) -> None:
        """Apply a ``custom_fields`` dict from an API payload."""
        if payload is None:
            return
        if not isinstance(payload, dict):
            return
        if merge:
            merged = dict(getattr(entity, "custom_fields", None) or {})
            merged.update(payload)
            entity.custom_fields = merged
        else:
            entity.custom_fields = payload

    @staticmethod
    def serialize_for_api(entity) -> Dict[str, Any]:
        """Return custom fields for API responses."""
        return dict(getattr(entity, "custom_fields", None) or {})

    @staticmethod
    def definitions_by_key(definitions: List[Any]) -> Dict[str, Any]:
        return {d.field_key: d for d in definitions}
