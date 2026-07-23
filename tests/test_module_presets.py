"""
Tests for first-run module presets.

Every module in the registry defaults to enabled, which meant a brand-new instance
presented all 41 of them at once. The setup wizard now offers a preset that writes
Settings.disabled_module_ids so unused areas start switched off.
"""

import pytest
from unittest.mock import patch

from app.models import Settings
from app.utils.module_registry import ModuleCategory, ModulePreset, ModuleRegistry

pytestmark = [pytest.mark.unit]


class TestPresetMembership:
    """The preset -> module mapping itself."""

    def test_every_module_belongs_to_everything_preset(self):
        ModuleRegistry.initialize_defaults()
        for module_id, module in ModuleRegistry.get_all().items():
            assert ModulePreset.EVERYTHING.value in module.presets, module_id

    def test_everything_preset_disables_nothing(self):
        assert ModuleRegistry.get_disabled_ids_for_preset(ModulePreset.EVERYTHING.value) == []

    def test_unknown_preset_disables_nothing(self):
        """An unrecognised value must fall back to the historical default."""
        assert ModuleRegistry.get_disabled_ids_for_preset("not-a-preset") == []
        assert ModuleRegistry.get_disabled_ids_for_preset("") == []

    def test_presets_are_progressively_larger(self):
        solo = set(ModuleRegistry.get_disabled_ids_for_preset(ModulePreset.SOLO.value))
        team = set(ModuleRegistry.get_disabled_ids_for_preset(ModulePreset.TEAM.value))
        compliance = set(ModuleRegistry.get_disabled_ids_for_preset(ModulePreset.COMPLIANCE.value))

        # Each preset enables a superset of the previous one, so it disables a subset.
        assert compliance < team < solo

    def test_solo_preset_meaningfully_reduces_surface(self):
        """The whole point: a solo user should not face all 41 modules."""
        total = len(ModuleRegistry.get_all())
        disabled = ModuleRegistry.get_disabled_ids_for_preset(ModulePreset.SOLO.value)
        assert total - len(disabled) <= 20

    def test_solo_preset_keeps_the_core_workflow(self):
        """Track time -> project/client -> invoice -> report must survive."""
        disabled = set(ModuleRegistry.get_disabled_ids_for_preset(ModulePreset.SOLO.value))
        for essential in ("timer", "projects", "clients", "invoices", "reports", "tasks"):
            assert essential not in disabled, essential


class TestPresetSafety:
    """A preset must never produce a state an admin could not save by hand."""

    @pytest.mark.parametrize("preset", [p.value for p in ModulePreset])
    def test_never_disables_a_core_module(self, preset):
        ModuleRegistry.initialize_defaults()
        for module_id in ModuleRegistry.get_disabled_ids_for_preset(preset):
            module = ModuleRegistry.get(module_id)
            assert module.category != ModuleCategory.CORE, module_id

    @pytest.mark.parametrize("preset", [p.value for p in ModulePreset])
    def test_never_breaks_a_dependency(self, preset):
        ModuleRegistry.initialize_defaults()
        disabled = set(ModuleRegistry.get_disabled_ids_for_preset(preset))
        enabled = set(ModuleRegistry.get_all()) - disabled
        for module_id in enabled:
            for dep in ModuleRegistry.get(module_id).dependencies:
                assert dep not in disabled, f"{module_id} depends on disabled {dep}"


@pytest.mark.integration
class TestSetupWizardPreset:
    """The wizard step that applies a preset."""

    def test_wizard_offers_every_preset(self, client, installation_config):
        with patch("app.routes.setup.get_installation_config") as mock_config:
            mock_config.return_value = installation_config
            response = client.get("/setup")
            assert response.status_code == 200
            html = response.get_data(as_text=True)
            assert 'name="module_preset"' in html
            for preset in ModulePreset:
                assert f'value="{preset.value}"' in html

    def test_submitting_solo_preset_disables_modules(self, app, client, installation_config):
        with patch("app.routes.setup.get_installation_config") as mock_config:
            mock_config.return_value = installation_config
            client.post("/setup", data={"timezone": "UTC", "module_preset": ModulePreset.SOLO.value})

        with app.app_context():
            settings = Settings.get_settings()
            expected = ModuleRegistry.get_disabled_ids_for_preset(ModulePreset.SOLO.value)
            assert sorted(settings.disabled_module_ids or []) == sorted(expected)
            assert settings.disabled_module_ids, "solo preset should disable something"

    def test_omitting_preset_keeps_everything_enabled(self, app, client, installation_config):
        """Backwards compatibility: an older form post must not disable modules."""
        with patch("app.routes.setup.get_installation_config") as mock_config:
            mock_config.return_value = installation_config
            client.post("/setup", data={"timezone": "UTC"})

        with app.app_context():
            settings = Settings.get_settings()
            assert (settings.disabled_module_ids or []) == []
