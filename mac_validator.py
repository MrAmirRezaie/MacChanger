"""
MAC Address Validator - Validates MAC addresses against real vendor patterns.
"""

import re
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
# This is a sampling of real vendor MAC prefixes
REAL_VENDOR_MACS = {
    # Intel
    "00:25:86": "Intel Corporate",
    "00:1A:A0": "Intel",
    "00:0D:B9": "Intel",
    # Realtek
    "52:54:00": "Realtek",
    "00:E0:4C": "Realtek",
    # Broadcom
    "00:10:18": "Broadcom",
    "00:04:75": "Broadcom",
    # Atheros
    "00:03:7F": "Atheros",
    "00:30:B6": "Atheros",
    # Qualcomm
    "00:1A:B3": "Qualcomm",
    # Cisco
    "00:12:D9": "Cisco",
    "00:1F:CA": "Cisco",
    # Apple
    "00:03:93": "Apple",
    "00:0A:95": "Apple",
    "A4:5E:60": "Apple",
    # Dell
    "00:14:22": "Dell",
    "00:01:AF": "Dell",
    # HP
    "00:04:EA": "HP",
    "00:1A:4B": "HP",
    # Lenovo/IBM
    "00:1A:2B": "Lenovo",
    "00:02:2D": "IBM",
    # Microsoft/Hyper-V
    "00:15:5D": "Microsoft",
    "52:54:00": "QEMU/KVM",
    # Generic valid patterns
    "00:11:22": "Generic Device",
    "00:AA:BB": "Generic Device",
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
        # Remove dots and dashes
        mac = mac.replace(".", "").replace("-", "")
        # Ensure uppercase
        mac = mac.upper()
        # Remove existing colons to handle mixed formats
        mac = mac.replace(":", "")
        # Add colons if we have 12 hex characters
        if len(mac) == 12 and all(c in "0123456789ABCDEF" for c in mac):
            mac = ":".join(mac[i : i + 2] for i in range(0, 12, 2))
        return mac

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


if __name__ == "__main__":
    test_validator()
