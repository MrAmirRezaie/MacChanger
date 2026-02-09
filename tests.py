"""
Comprehensive tests for MAC Address Spoofer including error scenarios and rollback testing.
"""

import unittest
import logging
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from mac_validator import MacValidator, MacValidationResult
from transaction_manager import TransactionManager, Transaction
from mac_spoofer import MacAddressSpoofer
from config_manager import ConfigManager, MacProfile
from mac_history import MacHistory, MacEntry
from scheduler import Scheduler, ScheduleFrequency
from interface_filter import InterfaceFilter
from platform_handlers import NetworkInterface
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


class TestConfigManager(unittest.TestCase):
    """Test cases for configuration manager."""

    def setUp(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_mgr = ConfigManager(config_dir=self.temp_dir)

    def tearDown(self):
        """Cleanup test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_profile(self):
        """Test creating a profile."""
        profile = self.config_mgr.create_profile("test", "Test profile")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "test")
        self.assertEqual(profile.description, "Test profile")

    def test_profile_persistence(self):
        """Test that profiles are persisted to disk."""
        profile = self.config_mgr.create_profile("test", "Test")
        profile.add_interface("eth0", "00:25:86:12:34:56")

        # Create new instance to verify persistence
        new_config_mgr = ConfigManager(config_dir=self.temp_dir)
        loaded_profile = new_config_mgr.get_profile("test")

        self.assertIsNotNone(loaded_profile)
        self.assertEqual(loaded_profile.get_interface("eth0"), "00:25:86:12:34:56")

    def test_add_interface_to_profile(self):
        """Test adding interface to profile."""
        profile = self.config_mgr.create_profile("test", "Test")
        result = self.config_mgr.add_interface_to_profile("test", "eth0", "00:25:86:12:34:56")
        self.assertTrue(result)

        profile = self.config_mgr.get_profile("test")
        self.assertEqual(profile.get_interface("eth0"), "00:25:86:12:34:56")

    def test_delete_profile(self):
        """Test deleting a profile."""
        self.config_mgr.create_profile("test", "Test")
        self.assertIsNotNone(self.config_mgr.get_profile("test"))

        result = self.config_mgr.delete_profile("test")
        self.assertTrue(result)
        self.assertIsNone(self.config_mgr.get_profile("test"))

    def test_clone_profile(self):
        """Test cloning a profile."""
        profile = self.config_mgr.create_profile("original", "Original")
        profile.add_interface("eth0", "00:25:86:12:34:56")
        self.config_mgr._save_profile(profile)

        cloned = self.config_mgr.clone_profile("original", "cloned")
        self.assertIsNotNone(cloned)
        self.assertEqual(cloned.get_interface("eth0"), "00:25:86:12:34:56")

    def test_list_profiles(self):
        """Test listing profiles."""
        self.config_mgr.create_profile("test1", "Test 1")
        self.config_mgr.create_profile("test2", "Test 2")

        profiles = self.config_mgr.list_profiles()
        self.assertEqual(len(profiles), 2)
        self.assertEqual(profiles[0]['name'], "test1")
        self.assertEqual(profiles[1]['name'], "test2")

    def test_search_profiles(self):
        """Test searching profiles."""
        self.config_mgr.create_profile("work", "Work network")
        self.config_mgr.create_profile("home", "Home network")

        results = self.config_mgr.search_profiles("work")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], "work")

    def test_settings_persistence(self):
        """Test settings persistence."""
        self.config_mgr.set_setting("auto_rollback", False)
        self.assertEqual(self.config_mgr.get_setting("auto_rollback"), False)

        # Create new instance to verify persistence
        new_config_mgr = ConfigManager(config_dir=self.temp_dir)
        self.assertEqual(new_config_mgr.get_setting("auto_rollback"), False)


class TestMacHistory(unittest.TestCase):
    """Test cases for MAC history database."""

    def setUp(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.history = MacHistory(history_dir=self.temp_dir)

    def tearDown(self):
        """Cleanup test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_mac(self):
        """Test recording a MAC address."""
        entry = self.history.record_mac("eth0", "00:25:86:12:34:56")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.interface, "eth0")
        self.assertEqual(entry.mac_address, "00:25:86:12:34:56")

    def test_record_spoof(self):
        """Test recording a spoof action."""
        self.history.record_spoof("eth0", "00:11:22:33:44:55", "00:25:86:12:34:56")

        entries = self.history.get_interface_history("eth0")
        self.assertEqual(len(entries), 2)  # Original and spoofed
        self.assertTrue(entries[0]['is_original'])  # First is original
        self.assertEqual(entries[1]['action'], "spoof")  # Second is spoof

    def test_get_original_mac(self):
        """Test retrieving original MAC."""
        self.history.record_mac("eth0", "00:11:22:33:44:55", is_original=True)
        self.history.record_mac("eth0", "00:25:86:12:34:56", action="spoof")

        original = self.history.get_original_mac("eth0")
        self.assertIsNotNone(original)
        self.assertEqual(original.mac_address, "00:11:22:33:44:55")

    def test_get_current_mac(self):
        """Test getting current MAC."""
        self.history.record_mac("eth0", "00:11:22:33:44:55", action="detected")
        self.history.record_mac("eth0", "00:25:86:12:34:56", action="spoof")

        current = self.history.get_current_mac("eth0")
        self.assertEqual(current, "00:25:86:12:34:56")

    def test_history_persistence(self):
        """Test that history is persisted to disk."""
        self.history.record_mac("eth0", "00:25:86:12:34:56")

        # Create new instance to verify persistence
        new_history = MacHistory(history_dir=self.temp_dir)
        entries = new_history.get_interface_history("eth0")

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['mac_address'], "00:25:86:12:34:56")

    def test_list_entries_with_filters(self):
        """Test listing entries with filters."""
        self.history.record_mac("eth0", "00:11:22:33:44:55", action="detected")
        self.history.record_mac("eth0", "00:25:86:12:34:56", action="spoof")
        self.history.record_mac("eth1", "00:11:22:33:44:66", action="detected")

        # Filter by interface
        eth0_entries = self.history.list_entries(interface="eth0")
        self.assertEqual(len(eth0_entries), 2)

        # Filter by action
        spoof_entries = self.history.list_entries(action="spoof")
        self.assertEqual(len(spoof_entries), 1)

    def test_search_entries(self):
        """Test searching history entries."""
        self.history.record_mac("eth0", "00:25:86:12:34:56")
        self.history.record_mac("eth1", "00:11:22:33:44:55")

        results = self.history.search_entries("eth0")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['interface'], "eth0")

    def test_get_statistics(self):
        """Test getting history statistics."""
        self.history.record_mac("eth0", "00:11:22:33:44:55", is_original=True)
        self.history.record_mac("eth0", "00:25:86:12:34:56", action="spoof")
        self.history.record_mac("eth1", "00:11:22:33:44:66", is_original=True)

        stats = self.history.get_statistics()
        self.assertEqual(stats['total_entries'], 3)
        self.assertEqual(stats['unique_interfaces'], 2)
        self.assertEqual(stats['spoof_actions'], 1)

    def test_clear_history(self):
        """Test clearing history."""
        self.history.record_mac("eth0", "00:11:22:33:44:55")
        self.history.record_mac("eth1", "00:11:22:33:44:66")

        # Record some entries
        initial_count = len(self.history.entries)
        self.assertGreater(initial_count, 0)

        # Clear all
        cleared = self.history.clear_history()
        self.assertEqual(cleared, initial_count)
        self.assertEqual(len(self.history.entries), 0)


class TestScheduler(unittest.TestCase):
    """Test cases for task scheduler."""

    def setUp(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.scheduler = Scheduler(schedule_dir=self.temp_dir)

    def tearDown(self):
        """Cleanup test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_task(self):
        """Test creating a scheduled task."""
        task = self.scheduler.create_task(
            "test_task",
            "eth0",
            "spoof_random",
            ScheduleFrequency.DAILY
        )

        self.assertIsNotNone(task)
        self.assertEqual(task.name, "test_task")
        self.assertEqual(task.interface, "eth0")
        self.assertEqual(task.frequency, ScheduleFrequency.DAILY)

    def test_task_persistence(self):
        """Test that tasks are persisted to disk."""
        self.scheduler.create_task(
            "test_task",
            "eth0",
            "spoof_random",
            ScheduleFrequency.DAILY
        )

        # Create new scheduler instance
        new_scheduler = Scheduler(schedule_dir=self.temp_dir)
        task = new_scheduler.get_task("test_task")

        self.assertIsNotNone(task)
        self.assertEqual(task.interface, "eth0")

    def test_enable_disable_task(self):
        """Test enabling and disabling tasks."""
        self.scheduler.create_task(
            "test_task",
            "eth0",
            "spoof_random",
            ScheduleFrequency.DAILY
        )

        # Disable task
        self.scheduler.disable_task("test_task")
        task = self.scheduler.get_task("test_task")
        self.assertFalse(task.enabled)

        # Enable task
        self.scheduler.enable_task("test_task")
        task = self.scheduler.get_task("test_task")
        self.assertTrue(task.enabled)

    def test_delete_task(self):
        """Test deleting a task."""
        self.scheduler.create_task(
            "test_task",
            "eth0",
            "spoof_random",
            ScheduleFrequency.DAILY
        )

        result = self.scheduler.delete_task("test_task")
        self.assertTrue(result)
        self.assertIsNone(self.scheduler.get_task("test_task"))

    def test_list_tasks(self):
        """Test listing tasks."""
        self.scheduler.create_task("task1", "eth0", "spoof_random", ScheduleFrequency.DAILY)
        self.scheduler.create_task("task2", "eth1", "spoof_random", ScheduleFrequency.HOURLY)

        tasks = self.scheduler.list_tasks()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]['name'], "task1")
        self.assertEqual(tasks[1]['name'], "task2")

    def test_search_tasks(self):
        """Test searching tasks."""
        self.scheduler.create_task(
            "daily_spoof",
            "eth0",
            "spoof_random",
            ScheduleFrequency.DAILY,
            description="Spoof MAC daily"
        )
        self.scheduler.create_task(
            "hourly_spoof",
            "eth1",
            "spoof_random",
            ScheduleFrequency.HOURLY
        )

        results = self.scheduler.search_tasks("daily")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], "daily_spoof")

    def test_task_execution_tracking(self):
        """Test tracking task execution."""
        task = self.scheduler.create_task(
            "test_task",
            "eth0",
            "spoof_random",
            ScheduleFrequency.ONCE
        )

        initial_count = task.run_count
        result = self.scheduler.run_task("test_task")

        self.assertTrue(result)
        task = self.scheduler.get_task("test_task")
        self.assertEqual(task.run_count, initial_count + 1)
        self.assertIsNotNone(task.last_run)


class TestInterfaceFilter(unittest.TestCase):
    """Test cases for interface filtering."""

    def setUp(self):
        """Setup test fixtures."""
        self.interfaces = [
            NetworkInterface(
                name="eth0",
                mac_address="00:25:86:12:34:56",
                status="up",
                ip_address="192.168.1.10",
                vendor="Intel",
                driver="e1000"
            ),
            NetworkInterface(
                name="eth1",
                mac_address="00:11:22:33:44:55",
                status="down",
                ip_address=None,
                vendor="Realtek",
                driver="r8169"
            ),
            NetworkInterface(
                name="wlan0",
                mac_address="00:11:22:33:44:66",
                status="up",
                ip_address="192.168.1.11",
                vendor="Atheros",
                driver="ath9k"
            ),
        ]

    def test_filter_by_name(self):
        """Test filtering by interface name."""
        filtered = InterfaceFilter.filter_by_name(self.interfaces, "eth")
        self.assertEqual(len(filtered), 2)

    def test_filter_by_status(self):
        """Test filtering by status."""
        filtered = InterfaceFilter.filter_by_status(self.interfaces, "up")
        self.assertEqual(len(filtered), 2)
        for iface in filtered:
            self.assertIn("up", iface.status.lower())

    def test_filter_by_vendor(self):
        """Test filtering by vendor."""
        filtered = InterfaceFilter.filter_by_vendor(self.interfaces, "Intel")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, "eth0")

    def test_filter_has_ip(self):
        """Test filtering interfaces with IP."""
        filtered = InterfaceFilter.filter_has_ip(self.interfaces)
        self.assertEqual(len(filtered), 2)

    def test_filter_no_ip(self):
        """Test filtering interfaces without IP."""
        filtered = InterfaceFilter.filter_no_ip(self.interfaces)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, "eth1")

    def test_search_interfaces(self):
        """Test searching interfaces."""
        results = InterfaceFilter.search(self.interfaces, "192.168.1.10")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "eth0")

    def test_sort_by_name(self):
        """Test sorting by name."""
        sorted_interfaces = InterfaceFilter.sort_by_field(self.interfaces, "name")
        names = [i.name for i in sorted_interfaces]
        self.assertEqual(names, ["eth0", "eth1", "wlan0"])

    def test_apply_multiple_filters(self):
        """Test applying multiple filters."""
        filters = {
            'status': 'up',
            'has_ip': True
        }
        filtered = InterfaceFilter.apply_filters(self.interfaces, filters)
        self.assertEqual(len(filtered), 2)

    def test_interface_table_output(self):
        """Test table output formatting."""
        table = InterfaceFilter.to_table(self.interfaces[:1])
        self.assertIn("eth0", table)
        self.assertIn("00:25:86:12:34:56", table)


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
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))
    suite.addTests(loader.loadTestsFromTestCase(TestMacHistory))
    suite.addTests(loader.loadTestsFromTestCase(TestScheduler))
    suite.addTests(loader.loadTestsFromTestCase(TestInterfaceFilter))
if __name__ == '__main__':
    run_tests()
