"""
Configuration Manager - Manages profiles and settings for MAC address spoofing.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class MacProfile:
    """A profile containing MAC address mappings for multiple interfaces."""
    name: str
    description: str = ""
    interfaces: Dict[str, str] = field(default_factory=dict)  # interface -> MAC address
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)

    def update_modified_time(self) -> None:
        """Update the modified timestamp."""
        self.modified_at = datetime.now().isoformat()

    def add_interface(self, interface: str, mac_address: str) -> None:
        """Add or update an interface MAC mapping."""
        self.interfaces[interface] = mac_address
        self.update_modified_time()

    def remove_interface(self, interface: str) -> bool:
        """Remove an interface from the profile."""
        if interface in self.interfaces:
            del self.interfaces[interface]
            self.update_modified_time()
            return True
        return False

    def get_interface(self, interface: str) -> Optional[str]:
        """Get MAC address for an interface."""
        return self.interfaces.get(interface)

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return asdict(self)


class ConfigManager:
    """Manages MAC spoofing profiles and configuration settings."""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_dir: Directory to store configuration files. Defaults to ~/.mac-spoofer/
        """
        self.logger = logging.getLogger(__name__)

        if config_dir is None:
            config_dir = str(Path.home() / ".mac-spoofer")

        self.config_dir = Path(config_dir)
        self.profiles_dir = self.config_dir / "profiles"
        self.settings_file = self.config_dir / "settings.json"

        # Create directories if they don't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

        self.profiles: Dict[str, MacProfile] = {}
        self.settings: Dict[str, Any] = {}

        # Load existing configurations
        self._load_settings()
        self._load_all_profiles()

    def _load_settings(self) -> None:
        """Load settings from file."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f) or {}
                self.logger.debug(f"Loaded settings from {self.settings_file}")
            else:
                self.settings = self._get_default_settings()
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            self.settings = self._get_default_settings()

    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings."""
        return {
            "auto_rollback": True,
            "verify_changes": True,
            "realistic_mac_only": True,
            "strict_validation": False,
            "max_profiles": 50,
            "enable_history": True,
            "version": "1.0.0"
        }

    def _load_all_profiles(self) -> None:
        """Load all profiles from disk."""
        try:
            for profile_file in self.profiles_dir.glob("*.json"):
                try:
                    with open(profile_file, 'r') as f:
                        profile_data = json.load(f)
                        profile = MacProfile(**profile_data)
                        self.profiles[profile.name] = profile
                    self.logger.debug(f"Loaded profile: {profile.name}")
                except Exception as e:
                    self.logger.error(f"Error loading profile {profile_file}: {e}")
        except Exception as e:
            self.logger.error(f"Error loading profiles: {e}")

    def save_settings(self) -> bool:
        """Save settings to file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            self.logger.info(f"Settings saved to {self.settings_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting."""
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> bool:
        """Set a specific setting."""
        try:
            self.settings[key] = value
            self.save_settings()
            self.logger.debug(f"Setting '{key}' set to {value}")
            return True
        except Exception as e:
            self.logger.error(f"Error setting '{key}': {e}")
            return False

    def create_profile(
        self, name: str, description: str = "", tags: Optional[List[str]] = None
    ) -> Optional[MacProfile]:
        """
        Create a new profile.

        Args:
            name: Profile name
            description: Profile description
            tags: Optional list of tags

        Returns:
            Created MacProfile or None on error
        """
        if name in self.profiles:
            self.logger.warning(f"Profile '{name}' already exists")
            return None

        if len(self.profiles) >= self.get_setting("max_profiles", 50):
            self.logger.error(f"Maximum profiles ({self.get_setting('max_profiles')}) reached")
            return None

        profile = MacProfile(
            name=name,
            description=description,
            tags=tags or []
        )

        self.profiles[name] = profile
        self._save_profile(profile)
        self.logger.info(f"Profile created: {name}")
        return profile

    def _save_profile(self, profile: MacProfile) -> bool:
        """Save a profile to disk."""
        try:
            profile_file = self.profiles_dir / f"{profile.name}.json"
            with open(profile_file, 'w') as f:
                json.dump(profile.to_dict(), f, indent=2)
            self.logger.debug(f"Profile saved: {profile.name}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving profile {profile.name}: {e}")
            return False

    def get_profile(self, name: str) -> Optional[MacProfile]:
        """Get a profile by name."""
        return self.profiles.get(name)

    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all profiles with basic info."""
        result = []
        for profile in self.profiles.values():
            result.append({
                'name': profile.name,
                'description': profile.description,
                'interface_count': len(profile.interfaces),
                'created_at': profile.created_at,
                'modified_at': profile.modified_at,
                'tags': profile.tags
            })
        return sorted(result, key=lambda x: x['name'])

    def delete_profile(self, name: str) -> bool:
        """Delete a profile."""
        if name not in self.profiles:
            self.logger.warning(f"Profile '{name}' not found")
            return False

        try:
            profile_file = self.profiles_dir / f"{name}.json"
            if profile_file.exists():
                profile_file.unlink()

            del self.profiles[name]
            self.logger.info(f"Profile deleted: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting profile {name}: {e}")
            return False

    def add_interface_to_profile(
        self, profile_name: str, interface: str, mac_address: str
    ) -> bool:
        """Add an interface to a profile."""
        profile = self.get_profile(profile_name)
        if not profile:
            self.logger.error(f"Profile '{profile_name}' not found")
            return False

        try:
            profile.add_interface(interface, mac_address)
            self._save_profile(profile)
            self.logger.info(
                f"Interface '{interface}' added to profile '{profile_name}' with MAC {mac_address}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Error adding interface to profile: {e}")
            return False

    def remove_interface_from_profile(self, profile_name: str, interface: str) -> bool:
        """Remove an interface from a profile."""
        profile = self.get_profile(profile_name)
        if not profile:
            self.logger.error(f"Profile '{profile_name}' not found")
            return False

        try:
            if profile.remove_interface(interface):
                self._save_profile(profile)
                self.logger.info(f"Interface '{interface}' removed from profile '{profile_name}'")
                return True
            else:
                self.logger.warning(f"Interface '{interface}' not found in profile '{profile_name}'")
                return False
        except Exception as e:
            self.logger.error(f"Error removing interface from profile: {e}")
            return False

    def clone_profile(self, source_name: str, dest_name: str) -> Optional[MacProfile]:
        """Clone a profile to create a new one."""
        source_profile = self.get_profile(source_name)
        if not source_profile:
            self.logger.error(f"Source profile '{source_name}' not found")
            return None

        if dest_name in self.profiles:
            self.logger.error(f"Destination profile '{dest_name}' already exists")
            return None

        try:
            new_profile = MacProfile(
                name=dest_name,
                description=f"Clone of {source_name}",
                interfaces=dict(source_profile.interfaces),
                tags=list(source_profile.tags)
            )

            self.profiles[dest_name] = new_profile
            self._save_profile(new_profile)
            self.logger.info(f"Profile cloned: {source_name} -> {dest_name}")
            return new_profile
        except Exception as e:
            self.logger.error(f"Error cloning profile: {e}")
            return None

    def search_profiles(self, keyword: str) -> List[Dict[str, Any]]:
        """Search profiles by keyword in name, description, or tags."""
        keyword_lower = keyword.lower()
        results = []

        for profile in self.profiles.values():
            if (
                keyword_lower in profile.name.lower()
                or keyword_lower in profile.description.lower()
                or any(keyword_lower in tag.lower() for tag in profile.tags)
            ):
                results.append({
                    'name': profile.name,
                    'description': profile.description,
                    'interface_count': len(profile.interfaces),
                    'created_at': profile.created_at,
                    'tags': profile.tags
                })

        return results

    def export_profile(self, profile_name: str, export_path: str) -> bool:
        """Export a profile to a specific file."""
        profile = self.get_profile(profile_name)
        if not profile:
            self.logger.error(f"Profile '{profile_name}' not found")
            return False

        try:
            export_file = Path(export_path)
            with open(export_file, 'w') as f:
                json.dump(profile.to_dict(), f, indent=2)
            self.logger.info(f"Profile exported to {export_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting profile: {e}")
            return False

    def import_profile(self, import_path: str, profile_name: Optional[str] = None) -> Optional[MacProfile]:
        """Import a profile from a file."""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                self.logger.error(f"Import file not found: {import_path}")
                return None

            with open(import_file, 'r') as f:
                profile_data = json.load(f)

            profile_name = profile_name or profile_data.get('name')
            if not profile_name:
                self.logger.error("Profile name not provided and not in import file")
                return None

            if profile_name in self.profiles:
                self.logger.error(f"Profile '{profile_name}' already exists")
                return None

            profile_data['name'] = profile_name
            profile = MacProfile(**profile_data)
            self.profiles[profile_name] = profile
            self._save_profile(profile)
            self.logger.info(f"Profile imported: {profile_name}")
            return profile
        except Exception as e:
            self.logger.error(f"Error importing profile: {e}")
            return None

    def __str__(self) -> str:
        """String representation."""
        return (
            f"ConfigManager(profiles={len(self.profiles)}, "
            f"config_dir={self.config_dir})"
        )


def test_config_manager():
    """Test the configuration manager."""
    print("=" * 60)
    print("Configuration Manager Tests")
    print("=" * 60)

    logging.basicConfig(level=logging.INFO)

    cm = ConfigManager()

    # Test profile creation
    print("\nCreating profiles...")
    profile1 = cm.create_profile("work", "Work network interfaces", tags=["work"])
    profile2 = cm.create_profile("home", "Home network interfaces", tags=["home"])

    if profile1:
        profile1.add_interface("eth0", "00:25:86:AA:BB:CC")
        profile1.add_interface("eth1", "52:54:00:AA:BB:CC")
        cm._save_profile(profile1)
        print(f"✓ Created and configured profile: {profile1.name}")

    if profile2:
        profile2.add_interface("wlan0", "00:11:22:AA:BB:CC")
        cm._save_profile(profile2)
        print(f"✓ Created and configured profile: {profile2.name}")

    # Test listing profiles
    print("\nAll profiles:")
    for p in cm.list_profiles():
        print(f"  - {p['name']}: {p['interface_count']} interfaces")

    # Test settings
    print("\nSettings Management:")
    cm.set_setting("auto_rollback", False)
    print(f"  auto_rollback: {cm.get_setting('auto_rollback')}")

    print(f"\nConfigManager: {cm}")


if __name__ == "__main__":
    test_config_manager()
