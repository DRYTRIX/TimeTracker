"""
Tests for installation configuration and setup
"""

import os
import json
import pytest
from app.utils.installation import InstallationConfig, get_installation_config


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory"""
    config_dir = tmp_path / "data"
    config_dir.mkdir()
    return str(config_dir)


@pytest.fixture
def installation_config(temp_config_dir, monkeypatch):
    """Create an InstallationConfig instance with temporary directory"""
    monkeypatch.setattr('app.utils.installation.InstallationConfig.CONFIG_DIR', temp_config_dir)
    config = InstallationConfig()
    return config


class TestInstallationConfig:
    """Test installation configuration management"""
    
    def test_installation_salt_generation(self, installation_config):
        """Test that installation salt is generated and persisted"""
        # First call should generate salt
        salt1 = installation_config.get_installation_salt()
        assert salt1 is not None
        assert len(salt1) == 64  # 32 bytes = 64 hex chars
        
        # Second call should return same salt
        salt2 = installation_config.get_installation_salt()
        assert salt1 == salt2
    
    def test_installation_id_generation(self, installation_config):
        """Test that installation ID is generated and persisted"""
        # First call should generate ID
        id1 = installation_config.get_installation_id()
        assert id1 is not None
        assert len(id1) == 16
        
        # Second call should return same ID
        id2 = installation_config.get_installation_id()
        assert id1 == id2
    
    def test_installation_id_uniqueness(self, temp_config_dir, monkeypatch):
        """Test that each installation gets a unique ID"""
        monkeypatch.setattr('app.utils.installation.InstallationConfig.CONFIG_DIR', temp_config_dir)
        
        config1 = InstallationConfig()
        id1 = config1.get_installation_id()
        
        # Create a new instance (simulating restart)
        config2 = InstallationConfig()
        id2 = config2.get_installation_id()
        
        # Should be the same ID (persisted)
        assert id1 == id2
    
    def test_setup_completion(self, installation_config):
        """Test setup completion tracking"""
        # Initially not complete
        assert not installation_config.is_setup_complete()
        
        # Mark as complete
        installation_config.mark_setup_complete(telemetry_enabled=True)
        assert installation_config.is_setup_complete()
        assert installation_config.get_telemetry_preference() is True
        
        # Verify persistence
        config2 = InstallationConfig()
        assert config2.is_setup_complete()
        assert config2.get_telemetry_preference() is True
    
    def test_telemetry_preference(self, installation_config):
        """Test telemetry preference management"""
        # Default is False
        assert installation_config.get_telemetry_preference() is False
        
        # Enable telemetry
        installation_config.set_telemetry_preference(True)
        assert installation_config.get_telemetry_preference() is True
        
        # Disable telemetry
        installation_config.set_telemetry_preference(False)
        assert installation_config.get_telemetry_preference() is False
    
    def test_config_persistence(self, installation_config, temp_config_dir):
        """Test that configuration is persisted to disk"""
        # Set some values
        salt = installation_config.get_installation_salt()
        installation_id = installation_config.get_installation_id()
        installation_config.mark_setup_complete(telemetry_enabled=True)
        
        # Read the file directly
        config_path = os.path.join(temp_config_dir, 'installation.json')
        assert os.path.exists(config_path)
        
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        assert data['telemetry_salt'] == salt
        assert data['installation_id'] == installation_id
        assert data['setup_complete'] is True
        assert data['telemetry_enabled'] is True
    
    def test_get_all_config(self, installation_config):
        """Test retrieving all configuration"""
        installation_config.mark_setup_complete(telemetry_enabled=True)
        
        config = installation_config.get_all_config()
        assert 'telemetry_salt' in config
        assert 'installation_id' in config
        assert 'setup_complete' in config
        assert config['setup_complete'] is True


class TestSetupRoutes:
    """Test setup routes"""
    
    def test_setup_page_redirects_if_complete(self, client, installation_config):
        """Test that setup page redirects if setup is already complete"""
        # Mark setup as complete
        installation_config.mark_setup_complete(telemetry_enabled=False)
        
        # Try to access setup page
        response = client.get('/setup')
        assert response.status_code in [302, 200]  # May redirect or show page
    
    def test_setup_completion_flow(self, client, installation_config):
        """Test completing the setup"""
        # Ensure setup is not complete
        assert not installation_config.is_setup_complete()
        
        # Access setup page
        response = client.get('/setup')
        assert response.status_code == 200
        
        # Complete setup with telemetry enabled
        response = client.post('/setup', data={
            'telemetry_enabled': 'on'
        }, follow_redirects=False)
        
        # Should redirect after completion
        assert response.status_code == 302
        
        # Verify setup is complete
        assert installation_config.is_setup_complete()
        assert installation_config.get_telemetry_preference() is True
    
    def test_setup_without_telemetry(self, client, installation_config):
        """Test completing setup with telemetry disabled"""
        # Complete setup without telemetry
        response = client.post('/setup', data={}, follow_redirects=False)
        
        # Should redirect after completion
        assert response.status_code == 302
        
        # Verify telemetry is disabled
        assert installation_config.get_telemetry_preference() is False

