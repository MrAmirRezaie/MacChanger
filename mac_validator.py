"""
MAC Address Validator - Validates MAC addresses against real vendor patterns.
"""

import json
import random
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class MacValidationResult:
    """Result of MAC address validation."""
    is_valid: bool
    message: str
    vendor: Optional[str] = None
    is_unicast: bool = False
    is_locally_administered: bool = False


# Real OUI (Organizationally Unique Identifier) patterns from major vendors
# Comprehensive list of 60+ real vendor MAC prefixes for realistic generation
OUI_CACHE_FILE = Path.home() / '.mac-spoofer' / 'oui_cache.json'
OUI_SOURCE_URL = 'https://standards-oui.ieee.org/oui/oui.csv'

REAL_VENDOR_MACS = {
    # Intel
    "00:25:86": "Intel Corporate",
    "00:1A:A0": "Intel",
    "00:0D:B9": "Intel",
    "00:19:B9": "Intel",
    "00:23:14": "Intel",
    "A8:5E:45": "Intel",
    # Realtek (Semiconductor)
    "52:54:00": "Realtek",
    "00:E0:4C": "Realtek",
    "00:50:F2": "Realtek",
    "74:DA:38": "Realtek",
    # Broadcom
    "00:10:18": "Broadcom",
    "00:04:75": "Broadcom",
    "00:0B:85": "Broadcom",
    "BC:92:6B": "Broadcom",
    # Atheros Communications
    "00:03:7F": "Atheros",
    "00:30:B6": "Atheros",
    "00:11:95": "Atheros",
    "1C:7E:E5": "Atheros",
    # Qualcomm
    "00:1A:B3": "Qualcomm",
    "00:26:86": "Qualcomm",
    "00:11:50": "Qualcomm",
    # Cisco Systems
    "00:12:D9": "Cisco",
    "00:1F:CA": "Cisco",
    "00:0C:41": "Cisco",
    "00:1A:6C": "Cisco",
    "2C:B0:5D": "Cisco",
    # Apple Inc.
    "00:03:93": "Apple",
    "00:0A:95": "Apple",
    "A4:5E:60": "Apple",
    "AC:87:A3": "Apple",
    "C0:A0:BB": "Apple",
    "F0:18:98": "Apple",
    # Dell Inc.
    "00:14:22": "Dell",
    "00:01:AF": "Dell",
    "00:16:35": "Dell",
    "50:9A:4C": "Dell",
    # HP (Hewlett-Packard)
    "00:04:EA": "HP",
    "00:1A:4B": "HP",
    "00:30:EA": "HP",
    "50:E5:49": "HP",
    # Lenovo
    "00:1A:2B": "Lenovo",
    "00:21:6A": "Lenovo",
    "28:F1:0E": "Lenovo",
    # IBM
    "00:02:2D": "IBM",
    "00:05:5B": "IBM",
    "00:04:AC": "IBM",
    # Microsoft/Hyper-V
    "00:15:5D": "Microsoft",
    "00:0C:29": "VMware",
    # QEMU/KVM/Virtualization
    "52:54:00": "QEMU/KVM",
    "52:55:44": "QEMU",
    # Asus
    "00:1A:92": "ASUS",
    "BC:5F:F4": "ASUS",
    # TP-Link
    "04:18:D6": "TP-Link",
    "5C:F3:70": "TP-Link",
    # D-Link
    "00:15:E9": "D-Link",
    "00:26:86": "D-Link",
    # Linksys
    "00:13:10": "Linksys",
    "00:18:E7": "Linksys",
    # 3Com
    "00:01:03": "3Com",
    "00:60:97": "3Com",
    # NEC
    "00:00:4E": "NEC",
    "00:A0:DE": "NEC",
    # Panasonic
    "00:0A:FD": "Panasonic",
    "08:ED:B7": "Panasonic",
    # Sony
    "00:06:6B": "Sony",
    "00:1F:3B": "Sony",
    # Samsung
    "00:1A:8A": "Samsung",
    "E0:55:3D": "Samsung",
    # LG Electronics
    "00:1E:8F": "LG",
    "AC:64:17": "LG",
    # Toshiba
    "00:0C:6E": "Toshiba",
    "F8:34:41": "Toshiba",
    # Canon
    "00:1A:43": "Canon",
    "B0:35:9F": "Canon",
    # Xerox
    "00:00:93": "Xerox",
    "00:11:09": "Xerox",
    # Epson
    "00:0D:FE": "Epson",
    "00:AC:E2": "Epson",
    # Generic valid patterns
    "00:11:22": "Generic Device",
    "00:AA:BB": "Generic Device",
    "02:00:00": "Generic Unicast",
}


class MacValidator:
    """Validates MAC addresses against patterns and vendor OUIs."""

    # RFC 5342 MAC format: XX:XX:XX:XX:XX:XX or XXXXXXXXXXXX
    MAC_PATTERN_COLON = re.compile(r"^([0-9A-Fa-f]{2}:){5}([0-9A-Fa-f]{2})$")
    MAC_PATTERN_DASH = re.compile(r"^([0-9A-Fa-f]{2}-){5}([0-9A-Fa-f]{2})$")
    MAC_PATTERN_PLAIN = re.compile(r"^([0-9A-Fa-f]){12}$")

    @staticmethod
    def normalize_mac(mac: str) -> str:
        """Normalize MAC address to standard format (XX:XX:XX:XX:XX:XX)."""
        # Remove dots, dashes, and colons
        clean_mac = mac.replace(".", "").replace("-", "").replace(":", "").upper()
        # Add colons if we have 12 hex characters
        if len(clean_mac) == 12 and all(c in "0123456789ABCDEF" for c in clean_mac):
            return ":".join(clean_mac[i : i + 2] for i in range(0, 12, 2))
        # Add colons for 3-octet vendor prefixes as well
        if len(clean_mac) == 6 and all(c in "0123456789ABCDEF" for c in clean_mac):
            return ":".join(clean_mac[i : i + 2] for i in range(0, 6, 2))
        return clean_mac

    @staticmethod
    def is_valid_format(mac: str) -> bool:
        """Check if MAC address has valid format."""
        mac = MacValidator.normalize_mac(mac)
        return bool(
            MacValidator.MAC_PATTERN_COLON.match(mac)
            or MacValidator.MAC_PATTERN_DASH.match(mac)
        )

    @staticmethod
    def is_unicast(mac: str) -> bool:
        """Check if MAC address is unicast (least significant bit of first octet is 0)."""
        mac = MacValidator.normalize_mac(mac)
        first_octet = int(mac.split(":")[0], 16)
        return (first_octet & 1) == 0

    @staticmethod
    def is_locally_administered(mac: str) -> bool:
        """Check if MAC is locally administered (second least significant bit is 1)."""
        mac = MacValidator.normalize_mac(mac)
        first_octet = int(mac.split(":")[0], 16)
        return (first_octet & 2) == 2

    @staticmethod
    def get_vendor(mac: str) -> Optional[str]:
        """Get vendor name from MAC address OUI prefix."""
        mac = MacValidator.normalize_mac(mac)
        oui = ":".join(mac.split(":")[:3])

        # Check exact match
        if oui in REAL_VENDOR_MACS:
            return REAL_VENDOR_MACS[oui]

        # Accept as generic valid if format is correct
        return "Unknown/Generic Vendor"

    @staticmethod
    def _normalize_prefix(prefix: str) -> str:
        prefix = MacValidator.normalize_mac(prefix)
        return ":".join(prefix.split(":")[:3])

    @staticmethod
    def _generate_mac_from_prefix(prefix: str, locally_administered: bool = False) -> str:
        prefix = MacValidator._normalize_prefix(prefix)
        host = ":".join(f"{random.randint(0, 255):02X}" for _ in range(3))
        mac = f"{prefix}:{host}"
        if locally_administered:
            octets = mac.split(":")
            first = int(octets[0], 16)
            first = (first | 0x02) & 0xFE
            octets[0] = f"{first:02X}"
            mac = ":".join(octets)
        return mac

    @staticmethod
    def generate_locally_administered_mac(vendor_prefix: Optional[str] = None) -> str:
        """Generate a locally administered MAC address."""
        if vendor_prefix:
            prefix = MacValidator._normalize_prefix(vendor_prefix)
        else:
            prefix = random.choice(list(REAL_VENDOR_MACS.keys()))
        return MacValidator._generate_mac_from_prefix(prefix, locally_administered=True)

    @staticmethod
    def generate_vendor_specific_mac(vendor_prefix: Optional[str] = None) -> str:
        """Generate a MAC address using a specific vendor prefix."""
        if vendor_prefix:
            prefix = MacValidator._normalize_prefix(vendor_prefix)
        else:
            prefix = random.choice(list(REAL_VENDOR_MACS.keys()))
        return MacValidator._generate_mac_from_prefix(prefix, locally_administered=False)

    @staticmethod
    def load_cached_oui_database() -> None:
        """Load a cached OUI vendor database from disk."""
        try:
            if OUI_CACHE_FILE.exists():
                with open(OUI_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                for key, value in cached.items():
                    REAL_VENDOR_MACS[key.upper()] = value
        except Exception:
            pass

    @staticmethod
    def refresh_oui_database(source_url: Optional[str] = None) -> bool:
        """Refresh the vendor OUI database from an online source."""
        source_url = source_url or OUI_SOURCE_URL
        try:
            OUI_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(source_url, timeout=15) as response:
                data = response.read().decode('utf-8', errors='ignore')

            updated = {}
            for line in data.splitlines():
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 3:
                    continue
                prefix = parts[1].replace('-', ':').upper()
                if len(prefix) == 8:
                    updated[prefix] = parts[2]

            if updated:
                with open(OUI_CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(updated, f, indent=2)
                REAL_VENDOR_MACS.update(updated)
                return True
        except urllib.error.URLError:
            return False
        except Exception:
            return False

    @staticmethod
    def validate_for_interface(
        mac: str,
        interface_type: Optional[str] = None,
        driver: Optional[str] = None,
        interface_name: Optional[str] = None,
        must_be_unicast: bool = True,
        must_have_vendor: bool = False
    ) -> MacValidationResult:
        """Validate a MAC address against interface-specific restrictions."""
        result = MacValidator.validate(mac, must_be_unicast=must_be_unicast, must_have_vendor=must_have_vendor)
        if not result.is_valid:
            return result

        if interface_type:
            interface_type_lower = interface_type.lower()
            if interface_type_lower == 'wireless' and not MacValidator.is_locally_administered(mac):
                return MacValidationResult(
                    is_valid=False,
                    message=f"MAC {mac} must be locally administered for wireless interfaces",
                    vendor=result.vendor,
                    is_unicast=result.is_unicast,
                    is_locally_administered=result.is_locally_administered,
                )
            if interface_type_lower in ('bridge', 'virtual') and not MacValidator.is_unicast(mac):
                return MacValidationResult(
                    is_valid=False,
                    message=f"MAC {mac} must be unicast for {interface_type} interfaces",
                    vendor=result.vendor,
                    is_unicast=False,
                    is_locally_administered=result.is_locally_administered,
                )

        if driver:
            driver_lower = driver.lower()
            if 'veth' in driver_lower or 'vmnet' in driver_lower:
                # Virtual bridge drivers generally accept locally administered MACs.
                pass

        if interface_name and interface_name.startswith('lo'):
            return MacValidationResult(
                is_valid=False,
                message=f"Interface {interface_name} is loopback and cannot be spoofed",
                vendor=result.vendor,
                is_unicast=result.is_unicast,
                is_locally_administered=result.is_locally_administered,
            )

        return result

    @staticmethod
    def validate(
        mac: str, must_be_unicast: bool = True, must_have_vendor: bool = False
    ) -> MacValidationResult:
        """
        Validate a MAC address comprehensively.

        Args:
            mac: MAC address to validate
            must_be_unicast: Require unicast address
            must_have_vendor: Require known vendor (stricter validation)

        Returns:
            MacValidationResult with detailed validation info
        """
        mac = MacValidator.normalize_mac(mac)

        # Check format
        if not MacValidator.is_valid_format(mac):
            return MacValidationResult(
                is_valid=False,
                message=f"Invalid MAC format: {mac}",
            )

        # Check unicast requirement
        if must_be_unicast and not MacValidator.is_unicast(mac):
            return MacValidationResult(
                is_valid=False,
                message=f"MAC {mac} is multicast, not unicast",
                is_unicast=False,
            )

        # Get vendor
        vendor = MacValidator.get_vendor(mac)

        # Check vendor requirement
        if must_have_vendor and vendor == "Unknown/Generic Vendor":
            return MacValidationResult(
                is_valid=False,
                message=f"MAC {mac} doesn't match known vendor patterns",
                vendor=vendor,
                is_unicast=MacValidator.is_unicast(mac),
                is_locally_administered=MacValidator.is_locally_administered(mac),
            )

        return MacValidationResult(
            is_valid=True,
            message=f"Valid MAC address: {mac} ({vendor})",
            vendor=vendor,
            is_unicast=MacValidator.is_unicast(mac),
            is_locally_administered=MacValidator.is_locally_administered(mac),
        )

    @staticmethod
    def generate_realistic_mac(vendor_prefix: Optional[str] = None) -> str:
        """
        Generate a realistic MAC address based on real vendor patterns.

        Args:
            vendor_prefix: Optional vendor OUI prefix (e.g., "00:25:86" for Intel)

        Returns:
            A realistic MAC address
        """
        import random

        if vendor_prefix:
            # Use provided vendor prefix
            prefix = MacValidator.normalize_mac(vendor_prefix)
            oui = ":".join(prefix.split(":")[: 3])
        else:
            # Pick random real vendor
            oui = random.choice(list(REAL_VENDOR_MACS.keys()))

        # Generate random host part (last 3 octets)
        host = ":".join(f"{random.randint(0, 255):02X}" for _ in range(3))

        mac = f"{oui}:{host}"

        # Ensure it's unicast (clear bit 0 of first octet)
        octets = mac.split(":")
        first = int(octets[0], 16)
        first = first & ~1  # Clear least significant bit for unicast
        octets[0] = f"{first:02X}"

        return ":".join(octets)


def test_validator():
    """Test the MAC validator."""
    print("=" * 60)
    print("MAC Address Validator Tests")
    print("=" * 60)

    # Test valid MACs
    test_cases = [
        ("00:1A:A0:12:34:56", True, "Valid Intel MAC"),
        ("52:54:00:12:34:56", True, "Valid Realtek MAC"),
        ("FF:FF:FF:FF:FF:FF", False, "Broadcast (multicast)"),
        ("00:1A:A0:12:34:ZZ", False, "Invalid characters"),
        ("00:1A:A0:12:34", False, "Too short"),
        ("001AA01234567", False, "Invalid format"),
    ]

    print("\nValidation Tests:")
    print("-" * 60)
    for mac, expected_unicast, description in test_cases:
        result = MacValidator.validate(mac)
        status = "[OK]" if result.is_valid else "[FAIL]"
        print(f"{status} {description}")
        print(f"   MAC: {mac}")
        print(f"   Valid: {result.is_valid}, Unicast: {result.is_unicast}")
        print(f"   Message: {result.message}")
        print()

    print("\nGenerated Realistic MACs:")
    print("-" * 60)
    for _ in range(5):
        mac = MacValidator.generate_realistic_mac()
        result = MacValidator.validate(mac)
        print(f"Generated: {mac}")
        print(f"  Vendor: {result.vendor}, Unicast: {result.is_unicast}")


try:
    MacValidator.load_cached_oui_database()
except Exception:
    pass


if __name__ == "__main__":
    test_validator()
