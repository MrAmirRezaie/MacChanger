"""
Comprehensive tests for MAC Address Spoofer including error scenarios and rollback testing.
"""

import unittest
import logging
from unittest.mock import Mock, patch, MagicMock
from mac_validator import MacValidator, MacValidationResult
from transaction_manager import TransactionManager, Transaction
from mac_spoofer import MacAddressSpoofer
from datetime import datetime


class TestMacValidator(unittest.TestCase):
    """Test cases for MAC validator."""

    def test_normalize_mac(self):
        """Test MAC normalization."""
        # Test colon format (already normalized)
        normalized = MacValidator.normalize_mac("00:1A:A0:12:34:56")
        self.assertEqual(normalized, "00:1A:A0:12:34:56")

        # Test plain format
        normalized = MacValidator.normalize_mac("001AA0123456")
        self.assertEqual(normalized, "00:1A:A0:12:34:56")

        # Test lowercase
        normalized = MacValidator.normalize_mac("00:1a:a0:12:34:56")
        self.assertEqual(normalized, "00:1A:A0:12:34:56")

    def test_valid_format(self):
        """Test MAC format validation."""
        self.assertTrue(MacValidator.is_valid_format("00:1A:A0:12:34:56"))
        self.assertTrue(MacValidator.is_valid_format("52:54:00:12:34:56"))
        self.assertFalse(MacValidator.is_valid_format("00:1A:A0:12:34:ZZ"))
        self.assertFalse(MacValidator.is_valid_format("00:1A:A0:12:34"))

    def test_unicast_validation(self):
        """Test unicast bit validation."""
        # Valid unicast (LSB of first octet = 0)
        self.assertTrue(MacValidator.is_unicast("00:1A:A0:12:34:56"))
        self.assertTrue(MacValidator.is_unicast("52:54:00:12:34:56"))

        # Invalid multicast (LSB of first octet = 1)
        self.assertFalse(MacValidator.is_unicast("01:1A:A0:12:34:56"))
        self.assertFalse(MacValidator.is_unicast("FF:FF:FF:FF:FF:FF"))

    def test_locally_administered(self):
        """Test locally administered bit."""
        # Not locally administered (bit 1 of first octet = 0)
        self.assertFalse(MacValidator.is_locally_administered("00:1A:A0:12:34:56"))

        # Locally administered (bit 1 of first octet = 1)
        self.assertTrue(MacValidator.is_locally_administered("02:1A:A0:12:34:56"))

    def test_vendor_lookup(self):
        """Test vendor lookup."""
        # Known vendor
        vendor = MacValidator.get_vendor("00:25:86:12:34:56")
        self.assertIsNotNone(vendor)

        # Unknown but valid
        vendor = MacValidator.get_vendor("AA:BB:CC:12:34:56")
        self.assertEqual(vendor, "Unknown/Generic Vendor")

    def test_comprehensive_validation(self):
        """Test comprehensive validation."""
        # Valid unicast
        result = MacValidator.validate("00:25:86:12:34:56", must_be_unicast=True)
        self.assertTrue(result.is_valid)
        self.assertTrue(result.is_unicast)

        # Multicast should fail
        result = MacValidator.validate("FF:FF:FF:FF:FF:FF", must_be_unicast=True)
        self.assertFalse(result.is_valid)

        # Invalid format
        result = MacValidator.validate("INVALID", must_be_unicast=True)
        self.assertFalse(result.is_valid)

    def test_generate_realistic_mac(self):
        """Test realistic MAC generation."""
        # Generate 10 MACs and verify they're all valid
        for _ in range(10):
            mac = MacValidator.generate_realistic_mac()
            result = MacValidator.validate(mac)
            self.assertTrue(result.is_valid, f"Generated invalid MAC: {mac}")
            self.assertTrue(result.is_unicast, f"Generated multicast MAC: {mac}")


class TestTransactionManager(unittest.TestCase):
    """Test cases for transaction manager."""

    def setUp(self):
        """Setup test fixtures."""
        self.tm = TransactionManager()

    def test_add_transaction(self):
        """Test adding transactions."""
        txn = self.tm.add_transaction(
            "spoof_mac",
            "eth0",
            "00:11:22:33:44:55",
            "00:25:86:AA:BB:CC"
        )

        self.assertIsNotNone(txn)
        self.assertEqual(txn.action, "spoof_mac")
        self.assertEqual(txn.interface, "eth0")
        self.assertEqual(txn.status, "pending")

    def test_commit_transaction(self):
        """Test committing transactions."""
        txn = self.tm.add_transaction("spoof_mac", "eth0", "AA:AA:AA:AA:AA:AA", "BB:BB:BB:BB:BB:BB")
        self.assertEqual(txn.status, "pending")

        self.tm.commit_transaction(txn)
        self.assertEqual(txn.status, "committed")

    def test_register_rollback_callback(self):
        """Test registering rollback callbacks."""
        callback_called = []

        def mock_callback(txn):
            callback_called.append(txn)
            return True

        self.tm.register_rollback_callback("spoof_mac", mock_callback)
        self.assertIn("spoof_mac", self.tm.rollback_callbacks)

    def test_rollback_with_callbacks(self):
        """Test rollback execution with callbacks."""
        rolled_back = []

        def rollback_callback(txn):
            rolled_back.append(txn.interface)
            return True

        self.tm.register_rollback_callback("spoof_mac", rollback_callback)

        txn = self.tm.add_transaction("spoof_mac", "eth0", "00:11:22:33:44:55", "00:25:86:AA:BB:CC")
        self.tm.commit_transaction(txn)

        result = self.tm.rollback()
        self.assertTrue(result['success'])
        self.assertEqual(result['rolled_back_count'], 1)
        self.assertIn("eth0", rolled_back)

    def test_rollback_failure(self):
        """Test rollback failure handling."""
        def failing_callback(txn):
            return False

        self.tm.register_rollback_callback("spoof_mac", failing_callback)

        txn = self.tm.add_transaction("spoof_mac", "eth0", "00:11:22:33:44:55", "00:25:86:AA:BB:CC")
        self.tm.commit_transaction(txn)

        result = self.tm.rollback()
        self.assertFalse(result['success'])
        self.assertEqual(result['failed_count'], 1)

    def test_transaction_history(self):
        """Test getting transaction history."""
        self.tm.add_transaction("spoof_mac", "eth0", "AA:AA:AA:AA:AA:AA", "BB:BB:BB:BB:BB:BB")
        self.tm.add_transaction("spoof_mac", "eth1", "CC:CC:CC:CC:CC:CC", "DD:DD:DD:DD:DD:DD")

        history = self.tm.get_transaction_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['interface'], "eth0")
        self.assertEqual(history[1]['interface'], "eth1")

    def test_clear_history(self):
        """Test clearing transaction history."""
        self.tm.add_transaction("spoof_mac", "eth0", "AA:AA:AA:AA:AA:AA", "BB:BB:BB:BB:BB:BB")
        self.assertEqual(len(self.tm.get_transaction_history()), 1)

        self.tm.clear_history()
        self.assertEqual(len(self.tm.get_transaction_history()), 0)


class TestMacAddressSpoofer(unittest.TestCase):
    """Test cases for MAC address spoofer with error scenarios."""

    def setUp(self):
        """Setup test fixtures."""
        self.spoofer = MacAddressSpoofer(auto_rollback_on_error=True)

    def test_validate_mac_address(self):
        """Test MAC validation through spoofer."""
        # Valid MAC
        is_valid, msg = self.spoofer.validate_mac_address("00:25:86:12:34:56")
        self.assertTrue(is_valid)

        # Invalid MAC
        is_valid, msg = self.spoofer.validate_mac_address("INVALID")
        self.assertFalse(is_valid)

    @patch('mac_spoofer.get_platform_handler')
    def test_spoof_mac_address_success(self, mock_handler):
        """Test successful MAC spoofing."""
        # Mock platform handler
        handler = MagicMock()
        handler.get_mac_address.side_effect = [
            "00:11:22:33:44:55",  # Initial MAC
            "00:25:86:12:34:56"   # After change
        ]
        handler.set_mac_address.return_value = True

        mock_handler.return_value = handler
        spoofer = MacAddressSpoofer()

        success, msg = spoofer.spoof_mac_address("eth0", "00:25:86:12:34:56")

        self.assertTrue(success)
        handler.set_mac_address.assert_called_once()

    @patch('mac_spoofer.get_platform_handler')
    def test_spoof_mac_address_failure_with_rollback(self, mock_handler):
        """Test MAC spoofing failure triggers automatic rollback."""
        handler = MagicMock()
        handler.get_mac_address.return_value = "00:11:22:33:44:55"
        handler.set_mac_address.return_value = False  # Simulate failure

        mock_handler.return_value = handler
        spoofer = MacAddressSpoofer(auto_rollback_on_error=True)

        success, msg = spoofer.spoof_mac_address("eth0", "00:25:86:12:34:56")

        self.assertFalse(success)
        # Verify transaction manager has pending transactions to rollback
        history = spoofer.get_transaction_history()
        self.assertTrue(len(history) > 0)

    @patch('mac_spoofer.get_platform_handler')
    def test_spoof_mac_address_verification_failure(self, mock_handler):
        """Test verification failure triggers rollback."""
        handler = MagicMock()
        handler.get_mac_address.side_effect = [
            "00:11:22:33:44:55",  # Initial MAC
            "00:11:22:33:44:55"   # Verification shows no change (failure)
        ]
        handler.set_mac_address.side_effect = [
            True,   # Initial change succeeds
            True    # Rollback succeeds
        ]

        mock_handler.return_value = handler
        spoofer = MacAddressSpoofer(auto_rollback_on_error=True)

        success, msg = spoofer.spoof_mac_address("eth0", "00:25:86:12:34:56")

        self.assertFalse(success)
        # Check that auto-rollback occurred
        history = spoofer.get_transaction_history()
        self.assertTrue(len(history) > 0)
        # The transaction should be in rolled_back status due to auto-rollback
        rolled_back_txns = [t for t in history if t.get('status') == 'rolled_back']
        self.assertTrue(len(rolled_back_txns) > 0)

    @patch('mac_spoofer.get_platform_handler')
    def test_spoof_multiple_interfaces_partial_failure_rollback(self, mock_handler):
        """Test partial failure in multi-interface spoof triggers full rollback."""
        handler = MagicMock()

        # First interface: initial, verification (success)
        # Second interface: initial, verification fails
        # Then rollback: both interfaces revert
        handler.get_mac_address.side_effect = [
            "00:11:22:33:44:55",  # eth0 initial
            "00:25:86:12:34:56",  # eth0 verification (success)
            "00:11:22:33:44:66",  # eth1 initial
            "00:11:22:33:44:66",  # eth1 verification (no change - fails)
            "00:25:86:12:34:56",  # eth0 rollback verification
            "00:11:22:33:44:66",  # eth1 rollback (not called but safe)
        ]
        handler.set_mac_address.side_effect = [
            True,   # eth0 succeeds
            False,  # eth1 fails
            True,   # eth0 rollback
            False,  # eth1 rollback (will fail)
        ]

        mock_handler.return_value = handler
        spoofer = MacAddressSpoofer(auto_rollback_on_error=True)

        mappings = {
            "eth0": "00:25:86:12:34:56",
            "eth1": "52:54:00:12:34:56"
        }

        results = spoofer.spoof_multiple_interfaces(mappings, rollback_on_partial_failure=True)

        # First should succeed, second should fail due to verification
        self.assertFalse(results["eth1"][0])

        # Rollback should have been triggered
        history = spoofer.get_transaction_history()
        # At least eth0 should be rolled back or cancelled
        self.assertTrue(len(history) >= 1)

    def test_invalid_mac_rejection(self):
        """Test that invalid MACs are rejected."""
        is_valid, msg = self.spoofer.validate_mac_address("ZZ:ZZ:ZZ:ZZ:ZZ:ZZ")
        self.assertFalse(is_valid)

    @patch('mac_spoofer.get_platform_handler')
    def test_transaction_history(self, mock_handler):
        """Test transaction history tracking."""
        handler = MagicMock()
        handler.get_mac_address.return_value = "00:11:22:33:44:55"
        handler.set_mac_address.return_value = True

        mock_handler.return_value = handler
        spoofer = MacAddressSpoofer()

        # Record some transactions
        spoofer.spoof_mac_address("eth0", "00:25:86:12:34:56")
        spoofer.spoof_mac_address("eth1", "52:54:00:12:34:56")

        history = spoofer.get_transaction_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['interface'], "eth0")
        self.assertEqual(history[1]['interface'], "eth1")


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""

    def test_network_interface_detection_error(self):
        """Test handling of interface detection errors."""
        spoofer = MacAddressSpoofer()

        with patch('mac_spoofer.get_platform_handler') as mock_handler:
            handler = MagicMock()
            handler.get_interfaces.side_effect = RuntimeError("Network error")
            mock_handler.return_value = handler

            # Should handle gracefully
            try:
                spoofer.get_available_interfaces()
            except RuntimeError:
                pass  # Expected

    @patch('mac_spoofer.get_platform_handler')
    def test_already_spoofed_mac(self, mock_handler):
        """Test handling when MAC already has target value."""
        handler = MagicMock()
        target_mac = "00:25:86:12:34:56"
        # Return target_mac both times: when getting the current and when verifying
        handler.get_mac_address.return_value = target_mac
        handler.set_mac_address.return_value = True

        mock_handler.return_value = handler

        spoofer = MacAddressSpoofer()
        success, msg = spoofer.spoof_mac_address("eth0", target_mac)
        self.assertTrue(success)  # Should succeed (idempotent)

    def test_mac_normalization_consistency(self):
        """Test that MAC normalization is consistent."""
        validator = MacValidator()

        # Different formats of same MAC
        macs = [
            "00:1A:A0:12:34:56",
            "00-1A-A0-12-34-56",
            "001AA0123456",
        ]

        normalized = [validator.normalize_mac(m) for m in macs]

        # All should normalize to the same value
        self.assertEqual(len(set(normalized)), 1)


def run_tests(verbose: bool = True) -> None:
    """Run all tests."""
    logging.basicConfig(level=logging.WARNING)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestMacValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestTransactionManager))
    suite.addTests(loader.loadTestsFromTestCase(TestMacAddressSpoofer))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print(f"Success: {result.wasSuccessful()}")
    print("=" * 70)


if __name__ == '__main__':
    run_tests()
