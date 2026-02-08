"""
Transaction Manager - Handles rollback of MAC address changes on errors.
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime


@dataclass
class Transaction:
    """A single transaction record."""
    action: str
    interface: str
    original_value: str
    new_value: str
    timestamp: str
    status: str = "pending"  # pending, committed, rolled_back


class TransactionManager:
    """Manages transactions with automatic rollback on errors."""

    def __init__(self, max_transactions: int = 1000):
        self.transactions: List[Transaction] = []
        self.max_transactions = max_transactions
        self.logger = logging.getLogger(__name__)
        self.rollback_callbacks: Dict[str, List[Callable]] = {}

    def add_transaction(
        self,
        action: str,
        interface: str,
        original_value: str,
        new_value: str
    ) -> Transaction:
        """
        Add a transaction to the log.

        Args:
            action: The action performed (e.g., 'spoof_mac', 'spoof_driver')
            interface: The network interface affected
            original_value: The original value before change
            new_value: The new value after change

        Returns:
            The created Transaction object
        """
        if len(self.transactions) >= self.max_transactions:
            self.transactions.pop(0)  # Remove oldest if limit reached

        transaction = Transaction(
            action=action,
            interface=interface,
            original_value=original_value,
            new_value=new_value,
            timestamp=datetime.now().isoformat(),
            status="pending"
        )

        self.transactions.append(transaction)
        self.logger.debug(
            f"Transaction added: {action} on {interface} "
            f"({original_value} -> {new_value})"
        )

        return transaction

    def commit_transaction(self, transaction: Transaction) -> None:
        """Mark a transaction as committed."""
        transaction.status = "committed"
        self.logger.debug(f"Transaction committed: {transaction.action} on {transaction.interface}")

    def register_rollback_callback(
        self, action: str, callback: Callable[[Transaction], bool]
    ) -> None:
        """
        Register a callback function to rollback an action.

        Args:
            action: The action type to rollback
            callback: Function that takes a Transaction and returns True if successful
        """
        if action not in self.rollback_callbacks:
            self.rollback_callbacks[action] = []
        self.rollback_callbacks[action].append(callback)
        self.logger.debug(f"Rollback callback registered for action: {action}")

    def rollback(self, transaction: Optional[Transaction] = None) -> Dict[str, Any]:
        """
        Rollback all or a specific transaction.

        Args:
            transaction: Specific transaction to rollback, or None for all

        Returns:
            Dict with rollback status and results
        """
        results = {
            "success": True,
            "rolled_back_count": 0,
            "failed_count": 0,
            "failed_transactions": []
        }

        # Determine which transactions to rollback
        if transaction:
            transactions_to_rollback = [transaction]
        else:
            transactions_to_rollback = [
                t for t in self.transactions if t.status == "committed"
            ]

        # Rollback in reverse order (LIFO)
        for txn in reversed(transactions_to_rollback):
            if txn.status == "rolled_back":
                continue

            self.logger.info(
                f"Attempting rollback: {txn.action} on {txn.interface} "
                f"({txn.new_value} -> {txn.original_value})"
            )

            success = self._execute_rollback(txn)

            if success:
                txn.status = "rolled_back"
                results["rolled_back_count"] += 1
            else:
                results["success"] = False
                results["failed_count"] += 1
                results["failed_transactions"].append({
                    "action": txn.action,
                    "interface": txn.interface,
                    "original_value": txn.original_value,
                    "new_value": txn.new_value
                })
                self.logger.error(
                    f"Failed to rollback: {txn.action} on {txn.interface}"
                )

        return results

    def _execute_rollback(self, transaction: Transaction) -> bool:
        """Execute the actual rollback for a transaction."""
        action = transaction.action

        if action not in self.rollback_callbacks:
            self.logger.warning(
                f"No rollback callback registered for action: {action}"
            )
            return False

        callbacks = self.rollback_callbacks[action]
        for callback in callbacks:
            try:
                if callback(transaction):
                    return True
            except Exception as e:
                self.logger.error(
                    f"Error in rollback callback for {action}: {e}"
                )

        return False

    def get_transaction_history(self) -> List[Dict[str, Any]]:
        """Get history of all transactions."""
        return [asdict(t) for t in self.transactions]

    def get_pending_transactions(self) -> List[Transaction]:
        """Get all pending transactions."""
        return [t for t in self.transactions if t.status == "pending"]

    def clear_history(self) -> None:
        """Clear all transaction history."""
        self.transactions.clear()
        self.logger.info("Transaction history cleared")

    def export_history(self, filepath: str) -> bool:
        """Export transaction history to JSON file."""
        try:
            history = self.get_transaction_history()
            with open(filepath, 'w') as f:
                json.dump(history, f, indent=2)
            self.logger.info(f"Transaction history exported to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to export transaction history: {e}")
            return False

    def __str__(self) -> str:
        """String representation of transaction manager state."""
        pending = len(self.get_pending_transactions())
        committed = len([t for t in self.transactions if t.status == "committed"])
        rolled_back = len([t for t in self.transactions if t.status == "rolled_back"])

        return (
            f"TransactionManager(total={len(self.transactions)}, "
            f"pending={pending}, committed={committed}, rolled_back={rolled_back})"
        )


def test_transaction_manager():
    """Test the transaction manager."""
    print("=" * 60)
    print("Transaction Manager Tests")
    print("=" * 60)

    # Setup logging
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

    tm = TransactionManager()

    # Add some test transactions
    print("\nAdding test transactions...")
    t1 = tm.add_transaction("spoof_mac", "eth0", "00:11:22:33:44:55", "00:25:86:AA:BB:CC")
    t2 = tm.add_transaction("spoof_mac", "eth1", "00:11:22:33:44:66", "52:54:00:AA:BB:CC")

    # Commit them
    tm.commit_transaction(t1)
    tm.commit_transaction(t2)

    print(f"\nTransaction Manager State: {tm}")
    print(f"Total transactions: {len(tm.get_transaction_history())}")

    # Register a simple rollback callback
    def mock_rollback(txn: Transaction) -> bool:
        print(f"  [ROLLBACK] Reverting {txn.interface} from {txn.new_value} to {txn.original_value}")
        return True

    tm.register_rollback_callback("spoof_mac", mock_rollback)

    # Test rollback
    print("\nTesting rollback...")
    results = tm.rollback()
    print(f"Rollback Results: {results}")

    print(f"\nFinal Transaction Manager State: {tm}")


if __name__ == "__main__":
    test_transaction_manager()
