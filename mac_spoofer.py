"""
MAC Address Spoofer - Main module with error detection and automatic rollback.
"""

import logging
from typing import Dict, List, Optional, Tuple
from mac_validator import MacValidator, MacValidationResult
from transaction_manager import TransactionManager, Transaction
from platform_handlers import (
    PlatformHandler,
    get_platform_handler,
    NetworkInterface
)


class MacAddressSpooferError(Exception):
    """Custom exception for MAC spoofing errors."""
    pass


class MacAddressSpoofer:
    """Main MAC address spoofer with transaction support and rollback."""

    def __init__(self, auto_rollback_on_error: bool = True):
        """
        Initialize the MAC spoofer.

        Args:
            auto_rollback_on_error: Automatically rollback on errors
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.platform_handler = get_platform_handler()
        self.transaction_manager = TransactionManager()
        self.auto_rollback_on_error = auto_rollback_on_error
        self._setup_rollback_handlers()

    def _setup_rollback_handlers(self) -> None:
        """Setup rollback callback handlers."""
        # Register rollback for MAC spoofing
        def rollback_mac_spoof(txn: Transaction) -> bool:
            try:
                original_mac = txn.original_value
                interface = txn.interface
                success = self.platform_handler.set_mac_address(interface, original_mac)

                if success:
                    self.logger.info(
                        f"Rolled back MAC on {interface} to {original_mac}"
                    )
                    return True
                else:
                    self.logger.error(f"Failed to rollback MAC on {interface}")
                    return False
            except Exception as e:
                self.logger.error(f"Error during MAC rollback: {e}")
                return False

        self.transaction_manager.register_rollback_callback(
            "spoof_mac",
            rollback_mac_spoof
        )

    def get_available_interfaces(self) -> List[Dict[str, str]]:
        """
        Get list of available network interfaces.

        Returns:
            List of interface info dicts
        """
        self.logger.info("Scanning network interfaces...")
        interfaces = self.platform_handler.get_interfaces()

        result = []
        for iface in interfaces:
            driver = self.platform_handler.get_driver_name(iface.name)
            result.append({
                'name': iface.name,
                'mac_address': iface.mac_address,
                'status': iface.status,
                'driver': driver or 'Unknown'
            })

        return result

    def validate_mac_address(
        self,
        mac: str,
        strict: bool = False
    ) -> Tuple[bool, str]:
        """
        Validate a MAC address.

        Args:
            mac: MAC address to validate
            strict: If True, require known vendor

        Returns:
            (is_valid, message)
        """
        result = MacValidator.validate(
            mac,
            must_be_unicast=True,
            must_have_vendor=strict
        )

        return result.is_valid, result.message

    def spoof_mac_address(
        self,
        interface: str,
        mac_address: str,
        force: bool = False
    ) -> Tuple[bool, str]:
        """
        Spoof MAC address of an interface.

        Args:
            interface: Network interface name
            mac_address: New MAC address
            force: Skip validation checks

        Returns:
            (success, message)
        """
        try:
            self.logger.info(f"Starting MAC spoof on {interface} to {mac_address}")

            # Validate MAC address
            if not force:
                is_valid, message = self.validate_mac_address(mac_address, strict=False)
                if not is_valid:
                    self.logger.error(f"Invalid MAC address: {message}")
                    return False, f"Invalid MAC: {message}"

            # Get current MAC
            current_mac = self.platform_handler.get_mac_address(interface)
            if not current_mac:
                msg = f"Could not retrieve current MAC for {interface}"
                self.logger.error(msg)
                return False, msg

            # Normalize MAC address
            current_mac = MacValidator.normalize_mac(current_mac)
            new_mac = MacValidator.normalize_mac(mac_address)

            if current_mac == new_mac:
                msg = f"Interface {interface} already has MAC {new_mac}"
                self.logger.info(msg)
                return True, msg

            # Add transaction before making changes
            txn = self.transaction_manager.add_transaction(
                action="spoof_mac",
                interface=interface,
                original_value=current_mac,
                new_value=new_mac
            )

            # Attempt to change MAC
            try:
                success = self.platform_handler.set_mac_address(interface, new_mac)

                if not success:
                    error_msg = f"Platform handler failed to set MAC on {interface}"
                    self.logger.error(error_msg)

                    if self.auto_rollback_on_error:
                        self.logger.warning("Auto-rollback triggered due to error")
                        self.transaction_manager.rollback(txn)

                    return False, error_msg

                # Verify the change
                verify_mac = self.platform_handler.get_mac_address(interface)
                verify_mac = MacValidator.normalize_mac(verify_mac) if verify_mac else None

                if verify_mac != new_mac:
                    error_msg = (
                        f"MAC verification failed on {interface}. "
                        f"Expected {new_mac}, got {verify_mac}"
                    )
                    self.logger.error(error_msg)

                    if self.auto_rollback_on_error:
                        self.logger.warning("Auto-rollback triggered due to verification failure")
                        self.transaction_manager.rollback(txn)

                    return False, error_msg

                # Commit the transaction
                self.transaction_manager.commit_transaction(txn)

                msg = f"Successfully spoofed MAC on {interface}: {current_mac} -> {new_mac}"
                self.logger.info(msg)
                return True, msg

            except Exception as e:
                error_msg = f"Exception during MAC spoof: {e}"
                self.logger.error(error_msg)

                if self.auto_rollback_on_error:
                    self.logger.warning("Auto-rollback triggered due to exception")
                    self.transaction_manager.rollback(txn)

                return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error in spoof_mac_address: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def spoof_multiple_interfaces(
        self,
        mappings: Dict[str, str],
        rollback_on_partial_failure: bool = True
    ) -> Dict[str, Tuple[bool, str]]:
        """
        Spoof MAC addresses on multiple interfaces.

        Args:
            mappings: Dict of {interface_name: new_mac_address}
            rollback_on_partial_failure: Rollback all on any failure

        Returns:
            Dict of {interface: (success, message)}
        """
        self.logger.info(f"Starting spoofing of {len(mappings)} interfaces")
        results = {}

        try:
            # Attempt all spoofs
            for interface, mac in mappings.items():
                success, message = self.spoof_mac_address(interface, mac)
                results[interface] = (success, message)

                if not success and rollback_on_partial_failure:
                    self.logger.error(
                        f"Failure detected on {interface}. Rolling back all changes..."
                    )
                    # Rollback all committed transactions
                    rollback_result = self.transaction_manager.rollback()
                    summary = (
                        f"Rollback summary: {rollback_result['rolled_back_count']} "
                        f"reverted, {rollback_result['failed_count']} failed"
                    )
                    self.logger.warning(summary)
                    # Mark remaining as cancelled
                    for remaining_interface in list(results.keys())[results[interface] != (success, message):]:
                        results[remaining_interface] = (False, "Cancelled due to partial failure")
                    break

            return results

        except Exception as e:
            self.logger.error(f"Exception in spoof_multiple_interfaces: {e}")
            # Rollback everything on exception
            if rollback_on_partial_failure:
                self.transaction_manager.rollback()
            return {iface: (False, str(e)) for iface in mappings}

    def generate_random_mac_for_interface(
        self,
        interface: str,
        realistic: bool = True
    ) -> Tuple[bool, str]:
        """
        Generate and spoof a random MAC address for an interface.

        Args:
            interface: Network interface name
            realistic: Generate realistic MAC from known vendors

        Returns:
            (success, new_mac_or_message)
        """
        try:
            # Generate realistic MAC
            if realistic:
                new_mac = MacValidator.generate_realistic_mac()
            else:
                # Generate random valid MAC
                import random
                octets = [f"{random.randint(0, 255):02X}" for _ in range(6)]
                # Ensure unicast (clear bit 0)
                first = int(octets[0], 16)
                first = first & ~1
                octets[0] = f"{first:02X}"
                new_mac = ":".join(octets)

            # Spoof the MAC
            success, message = self.spoof_mac_address(interface, new_mac)

            if success:
                return True, new_mac
            else:
                return False, message

        except Exception as e:
            self.logger.error(f"Error generating random MAC: {e}")
            return False, str(e)

    def get_transaction_history(self) -> List[Dict]:
        """Get transaction history."""
        return self.transaction_manager.get_transaction_history()

    def rollback_all_changes(self) -> Dict:
        """Manually rollback all changes."""
        self.logger.info("Manual rollback requested")
        return self.transaction_manager.rollback()

    def get_status(self) -> str:
        """Get status summary."""
        return str(self.transaction_manager)


def test_spoofer():
    """Test the MAC spoofer."""
    print("=" * 60)
    print("MAC Address Spoofer Tests")
    print("=" * 60)

    logging.basicConfig(level=logging.INFO)

    spoofer = MacAddressSpoofer()
    print(f"\nStatus: {spoofer.get_status()}")

    # Test interface detection
    print("\nDetecting interfaces...")
    print("-" * 60)
    interfaces = spoofer.get_available_interfaces()
    for iface in interfaces:
        print(f"  {iface['name']}: {iface['mac_address']} ({iface['status']})")
        print(f"    Driver: {iface['driver']}")

    # Test MAC validation
    print("\nTesting MAC validation...")
    print("-" * 60)
    test_macs = [
        "00:25:86:12:34:56",  # Intel - valid
        "FF:FF:FF:FF:FF:FF",  # Broadcast - invalid
        "INVALID",  # Invalid format
    ]

    for mac in test_macs:
        is_valid, msg = spoofer.validate_mac_address(mac)
        status = "✓" if is_valid else "✗"
        print(f"  {status} {mac}: {msg}")

    # Test random MAC generation
    print("\nGenerating realistic MAC addresses...")
    print("-" * 60)
    validator = MacValidator()
    for _ in range(3):
        mac = validator.generate_realistic_mac()
        print(f"  Generated: {mac}")


if __name__ == "__main__":
    test_spoofer()
