"""
MAC History Database - Maintains history of MAC address changes with backup/recovery.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class MacEntry:
    """A single MAC address history entry."""
    interface: str
    mac_address: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    action: str = "spoof"  # spoof, restore, detected
    status: str = "active"  # active, archived, restored
    notes: str = ""
    is_original: bool = False  # True if this is the original MAC before any spoofing

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MacHistory:
    """Manages MAC address history and backup/recovery."""

    def __init__(self, history_dir: Optional[str] = None):
        """
        Initialize MAC history database.

        Args:
            history_dir: Directory to store history files. Defaults to ~/.mac-spoofer/history/
        """
        self.logger = logging.getLogger(__name__)

        if history_dir is None:
            history_dir = str(Path.home() / ".mac-spoofer" / "history")

        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

        self.entries: List[MacEntry] = []
        self._load_history()

    def _load_history(self) -> None:
        """Load history from disk."""
        try:
            for history_file in self.history_dir.glob("*.json"):
                try:
                    with open(history_file, 'r') as f:
                        entries_data = json.load(f)
                        if isinstance(entries_data, list):
                            for entry_data in entries_data:
                                entry = MacEntry(**entry_data)
                                self.entries.append(entry)
                    self.logger.debug(f"Loaded history from {history_file}")
                except Exception as e:
                    self.logger.error(f"Error loading history {history_file}: {e}")
        except Exception as e:
            self.logger.error(f"Error loading history: {e}")

    def _save_history(self) -> bool:
        """Save entire history to disk."""
        try:
            # Save all entries to a single file
            history_file = self.history_dir / "mac_history.json"
            entries_dict = [entry.to_dict() for entry in self.entries]

            with open(history_file, 'w') as f:
                json.dump(entries_dict, f, indent=2)

            self.logger.debug(f"History saved to {history_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving history: {e}")
            return False

    def record_mac(
        self,
        interface: str,
        mac_address: str,
        action: str = "detected",
        notes: str = "",
        is_original: bool = False
    ) -> MacEntry:
        """
        Record a MAC address in history.

        Args:
            interface: Network interface name
            mac_address: MAC address to record
            action: Type of action (spoof, restore, detected)
            notes: Optional notes about this entry
            is_original: Whether this is the original MAC

        Returns:
            Created MacEntry
        """
        entry = MacEntry(
            interface=interface,
            mac_address=mac_address,
            action=action,
            notes=notes,
            is_original=is_original
        )

        self.entries.append(entry)
        self._save_history()
        self.logger.debug(
            f"Recorded MAC for {interface}: {mac_address} (action: {action})"
        )
        return entry

    def record_spoof(self, interface: str, original_mac: str, new_mac: str) -> None:
        """Record a MAC spoofing action."""
        # Record original if not already recorded
        original_entry = self.get_original_mac(interface)
        if not original_entry:
            self.record_mac(
                interface, original_mac, action="detected",
                notes="Original MAC detected at first record", is_original=True
            )

        # Record the new spoofed MAC
        self.record_mac(
            interface, new_mac, action="spoof",
            notes=f"Spoofed from {original_mac}"
        )

    def get_interface_history(self, interface: str) -> List[Dict[str, Any]]:
        """Get all history entries for a specific interface."""
        return [
            entry.to_dict() for entry in self.entries
            if entry.interface == interface
        ]

    def get_original_mac(self, interface: str) -> Optional[MacEntry]:
        """Get the original MAC address for an interface."""
        for entry in self.entries:
            if entry.interface == interface and entry.is_original:
                return entry
        return None

    def get_current_mac(self, interface: str) -> Optional[str]:
        """Get the most recent MAC address for an interface."""
        for entry in reversed(self.entries):
            if entry.interface == interface and entry.status == "active":
                return entry.mac_address
        return None

    def get_last_spoofed_mac(self, interface: str) -> Optional[MacEntry]:
        """Get the last spoofed MAC for an interface."""
        for entry in reversed(self.entries):
            if entry.interface == interface and entry.action == "spoof":
                return entry
        return None

    def get_all_interfaces(self) -> List[str]:
        """Get list of all interfaces in history."""
        interfaces = set()
        for entry in self.entries:
            interfaces.add(entry.interface)
        return sorted(list(interfaces))

    def restore_original_mac(self, interface: str) -> Optional[str]:
        """
        Get the original MAC address for restoration.

        Returns:
            Original MAC address or None if not found
        """
        original = self.get_original_mac(interface)
        return original.mac_address if original else None

    def list_entries(
        self,
        interface: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List history entries with optional filtering.

        Args:
            interface: Filter by interface name
            action: Filter by action type
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of matching entries (newest first)
        """
        results = []

        for entry in reversed(self.entries):
            if interface and entry.interface != interface:
                continue
            if action and entry.action != action:
                continue
            if status and entry.status != status:
                continue

            results.append(entry.to_dict())

            if limit and len(results) >= limit:
                break

        return results

    def search_entries(self, keyword: str) -> List[Dict[str, Any]]:
        """Search entries by interface, MAC, or notes."""
        keyword_lower = keyword.lower()
        results = []

        for entry in reversed(self.entries):
            if (
                keyword_lower in entry.interface.lower()
                or keyword_lower in entry.mac_address.lower()
                or keyword_lower in entry.notes.lower()
            ):
                results.append(entry.to_dict())

        return results

    def archive_entry(self, interface: str, mac_address: str) -> bool:
        """Archive a history entry."""
        for entry in self.entries:
            if entry.interface == interface and entry.mac_address == mac_address:
                entry.status = "archived"
                self._save_history()
                self.logger.info(f"Archived entry for {interface}: {mac_address}")
                return True
        return False

    def restore_entry_status(self, interface: str, mac_address: str) -> bool:
        """Mark an entry as restored."""
        for entry in self.entries:
            if entry.interface == interface and entry.mac_address == mac_address:
                entry.status = "restored"
                self._save_history()
                self.logger.info(f"Marked as restored for {interface}: {mac_address}")
                return True
        return False

    def clear_history(self, interface: Optional[str] = None) -> int:
        """
        Clear history entries.

        Args:
            interface: If specified, only clear entries for this interface

        Returns:
            Number of entries cleared
        """
        original_count = len(self.entries)

        if interface:
            self.entries = [e for e in self.entries if e.interface != interface]
            cleared = original_count - len(self.entries)
            self.logger.info(f"Cleared {cleared} entries for {interface}")
        else:
            self.entries.clear()
            self.logger.warning("Cleared all history entries")

        self._save_history()
        return original_count - len(self.entries)

    def export_history(self, export_path: str) -> bool:
        """Export history to a file."""
        try:
            export_file = Path(export_path)
            entries_dict = [entry.to_dict() for entry in self.entries]

            with open(export_file, 'w') as f:
                json.dump(entries_dict, f, indent=2)

            self.logger.info(f"History exported to {export_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting history: {e}")
            return False

    def import_history(self, import_path: str) -> int:
        """
        Import history from a file.

        Returns:
            Number of entries imported
        """
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                self.logger.error(f"Import file not found: {import_path}")
                return 0

            with open(import_file, 'r') as f:
                entries_data = json.load(f)

            original_count = len(self.entries)

            for entry_data in entries_data:
                entry = MacEntry(**entry_data)
                self.entries.append(entry)

            self._save_history()
            imported = len(self.entries) - original_count
            self.logger.info(f"Imported {imported} history entries from {import_path}")
            return imported
        except Exception as e:
            self.logger.error(f"Error importing history: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the history."""
        total_entries = len(self.entries)
        unique_interfaces = len(self.get_all_interfaces())
        unique_macs = len(set(e.mac_address for e in self.entries))

        spoof_actions = len([e for e in self.entries if e.action == "spoof"])
        restore_actions = len([e for e in self.entries if e.action == "restore"])

        return {
            'total_entries': total_entries,
            'unique_interfaces': unique_interfaces,
            'unique_macs': unique_macs,
            'spoof_actions': spoof_actions,
            'restore_actions': restore_actions,
            'archived_entries': len([e for e in self.entries if e.status == "archived"]),
            'active_entries': len([e for e in self.entries if e.status == "active"]),
            'restored_entries': len([e for e in self.entries if e.status == "restored"])
        }

    def __str__(self) -> str:
        """String representation."""
        return f"MacHistory(entries={len(self.entries)}, dir={self.history_dir})"


def test_mac_history():
    """Test the MAC history database."""
    print("=" * 60)
    print("MAC History Database Tests")
    print("=" * 60)

    logging.basicConfig(level=logging.INFO)

    history = MacHistory()

    # Record some MACs
    print("\nRecording MAC addresses...")
    history.record_mac("eth0", "00:11:22:33:44:55", action="detected", is_original=True)
    history.record_mac("eth0", "00:25:86:AA:BB:CC", action="spoof", notes="First spoof")
    history.record_mac("eth0", "52:54:00:AA:BB:CC", action="spoof", notes="Second spoof")

    history.record_mac("eth1", "00:11:22:33:44:66", action="detected", is_original=True)
    history.record_mac("eth1", "00:AA:BB:CC:DD:EE", action="spoof", notes="Home network")

    # Get interface history
    print("\nInterface history for eth0:")
    for entry in history.get_interface_history("eth0"):
        print(f"  {entry['timestamp']}: {entry['mac_address']} ({entry['action']})")

    # Get statistics
    print("\nStatistics:")
    stats = history.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print(f"\n{history}")


if __name__ == "__main__":
    test_mac_history()
