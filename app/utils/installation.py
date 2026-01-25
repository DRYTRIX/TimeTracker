"""
Installation and configuration utilities for TimeTracker

This module handles first-time setup, installation-specific configuration,
and telemetry salt generation.
"""

import os
import json
import secrets
import hashlib
from pathlib import Path
from typing import Dict, Optional


class InstallationConfig:
    """Manages installation-specific configuration"""

    CONFIG_DIR = "/data"  # default; overridden by INSTALLATION_CONFIG_DIR when set
    CONFIG_FILE = "installation.json"

    def __init__(self):
        effective_dir = os.environ.get("INSTALLATION_CONFIG_DIR", self.CONFIG_DIR)
        self.config_path = os.path.join(effective_dir, self.CONFIG_FILE)
        self._ensure_config_dir(effective_dir)
        self._config = self._load_config()

    def _ensure_config_dir(self, config_dir=None):
        """Ensure the configuration directory exists."""
        dir_path = config_dir if config_dir is not None else os.environ.get("INSTALLATION_CONFIG_DIR", self.CONFIG_DIR)
        os.makedirs(dir_path, exist_ok=True)

    def _load_config(self) -> Dict:
        """Load configuration from file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_config(self):
        """Save configuration to file.
        Merges with on-disk state so existing keys (e.g. setup_complete) are never dropped.
        """
        try:
            on_disk = self._load_config()
            self._config = {**on_disk, **self._config}
            with open(self.config_path, "w") as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f"Error saving installation config: {e}")

    def get_installation_salt(self) -> str:
        """
        Get or generate installation-specific salt for telemetry.

        This salt is unique per installation and persists across restarts.
        It's used to generate consistent anonymous fingerprints.
        """
        if "telemetry_salt" not in self._config:
            # Generate a unique 64-character hex salt
            salt = secrets.token_hex(32)  # 32 bytes = 64 hex characters
            self._config["telemetry_salt"] = salt
            self._save_config()
        return self._config["telemetry_salt"]

    def get_installation_id(self) -> str:
        """
        Get or generate a unique installation ID.

        This is a one-way hash that uniquely identifies this installation
        without revealing any server information.
        """
        if "installation_id" not in self._config:
            # Generate a unique installation ID
            import platform
            import time

            # Combine multiple factors for uniqueness
            factors = [platform.node() or "unknown", str(time.time()), secrets.token_hex(16)]

            # Hash to create installation ID
            combined = "".join(factors).encode()
            installation_id = hashlib.sha256(combined).hexdigest()[:16]

            self._config["installation_id"] = installation_id
            self._save_config()

        return self._config["installation_id"]

    def is_setup_complete(self) -> bool:
        """Check if initial setup is complete"""
        return self._config.get("setup_complete", False)

    def mark_setup_complete(self, telemetry_enabled: bool = False):
        """Mark initial setup as complete"""
        self._config["setup_complete"] = True
        self._config["telemetry_enabled"] = telemetry_enabled
        self._config["setup_completed_at"] = str(datetime.now())
        self._save_config()

    def is_initial_data_seeded(self) -> bool:
        """Check if initial database data (default client/project) has been seeded"""
        return self._config.get("initial_data_seeded", False)

    def mark_initial_data_seeded(self):
        """Mark that initial database data has been seeded"""
        self._config["initial_data_seeded"] = True
        self._config["initial_data_seeded_at"] = str(datetime.now())
        self._save_config()

    def get_telemetry_preference(self) -> bool:
        """Get user's telemetry preference.
        Uses a local load only; does not overwrite self._config to avoid poisoning
        the shared in-memory state when the on-disk file is corrupt or empty.
        """
        data = self._load_config()
        return data.get("telemetry_enabled", False)

    def set_telemetry_preference(self, enabled: bool):
        """Set user's telemetry preference"""
        self._config["telemetry_enabled"] = enabled
        self._save_config()

    def get_all_config(self) -> Dict:
        """Get all configuration (for admin dashboard)"""
        return self._config.copy()


# Global instance
_installation_config = None
_installation_config_path = None


def get_installation_config() -> InstallationConfig:
    """Get the global installation configuration instance"""
    global _installation_config, _installation_config_path
    # Reinitialize if config path changed (e.g., tests overriding directories)
    tmp = InstallationConfig()
    current_path = tmp.config_path
    if (_installation_config is None) or (_installation_config_path != current_path):
        _installation_config = tmp
        _installation_config_path = current_path
    return _installation_config


# Add missing datetime import
from datetime import datetime
