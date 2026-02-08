"""
MAC Address Spoofer - Command Line Interface
"""

import argparse
import logging
import sys
import json
from mac_spoofer import MacAddressSpoofer
from mac_validator import MacValidator
from platform_handlers import get_platform_handler


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def list_interfaces(args) -> int:
    """List available network interfaces."""
    print("\n" + "=" * 70)
    print("AVAILABLE NETWORK INTERFACES")
    print("=" * 70)

    spoofer = MacAddressSpoofer()
    interfaces = spoofer.get_available_interfaces()

    if not interfaces:
        print("No network interfaces found.")
        return 1

    for i, iface in enumerate(interfaces, 1):
        print(f"\n[{i}] {iface['name']}")
        print(f"    MAC Address: {iface['mac_address']}")
        print(f"    Status: {iface['status']}")
        print(f"    Driver: {iface['driver']}")

    print("\n" + "=" * 70)
    return 0


def validate_mac(args) -> int:
    """Validate a MAC address."""
    print("\n" + "=" * 70)
    print("MAC ADDRESS VALIDATION")
    print("=" * 70)

    mac = args.mac
    print(f"\nValidating: {mac}")

    is_valid, message = MacAddressSpoofer().validate_mac_address(mac, strict=args.strict)

    if is_valid:
        print(f"✓ {message}")
        validator = MacValidator()
        result = validator.validate(mac)
        if result.vendor:
            print(f"  Vendor: {result.vendor}")
        print(f"  Unicast: {result.is_unicast}")
        print(f"  Locally Administered: {result.is_locally_administered}")
        return 0
    else:
        print(f"✗ {message}")
        return 1


def spoof_mac(args) -> int:
    """Spoof MAC address of an interface."""
    print("\n" + "=" * 70)
    print("MAC ADDRESS SPOOFING")
    print("=" * 70)

    spoofer = MacAddressSpoofer(auto_rollback_on_error=not args.no_auto_rollback)

    interface = args.interface
    mac = args.mac
    force = args.force

    print(f"\nInterface: {interface}")
    print(f"New MAC: {mac}")
    print(f"Force: {force}")
    print(f"Auto-rollback on error: {not args.no_auto_rollback}")

    success, message = spoofer.spoof_mac_address(interface, mac, force=force)

    if success:
        print(f"\n✓ SUCCESS: {message}")
        print(f"\nStatus: {spoofer.get_status()}")
        return 0
    else:
        print(f"\n✗ FAILED: {message}")
        print(f"\nStatus: {spoofer.get_status()}")
        return 1


def spoof_random_mac(args) -> int:
    """Generate and spoof a random MAC address."""
    print("\n" + "=" * 70)
    print("RANDOM MAC ADDRESS SPOOFING")
    print("=" * 70)

    spoofer = MacAddressSpoofer(auto_rollback_on_error=not args.no_auto_rollback)

    interface = args.interface
    realistic = args.realistic

    print(f"\nInterface: {interface}")
    print(f"Realistic: {realistic}")

    success, result = spoofer.generate_random_mac_for_interface(interface, realistic=realistic)

    if success:
        print(f"\n✓ SUCCESS: Spoofed to {result}")
        print(f"\nStatus: {spoofer.get_status()}")
        return 0
    else:
        print(f"\n✗ FAILED: {result}")
        return 1


def generate_mac(args) -> int:
    """Generate a realistic MAC address without spoofing."""
    print("\n" + "=" * 70)
    print("GENERATE REALISTIC MAC ADDRESS")
    print("=" * 70)

    count = args.count
    print(f"\nGenerating {count} realistic MAC address(es)...\n")

    for _ in range(count):
        mac = MacValidator.generate_realistic_mac()
        is_valid, msg = MacAddressSpoofer().validate_mac_address(mac)
        status = "✓" if is_valid else "✗"
        print(f"{status} {mac}")

    return 0


def show_history(args) -> int:
    """Show transaction history."""
    print("\n" + "=" * 70)
    print("TRANSACTION HISTORY")
    print("=" * 70)

    spoofer = MacAddressSpoofer()
    history = spoofer.get_transaction_history()

    if not history:
        print("\nNo transactions recorded.")
        return 0

    for i, txn in enumerate(history, 1):
        print(f"\n[{i}] {txn['action'].upper()} - {txn['status'].upper()}")
        print(f"    Interface: {txn['interface']}")
        print(f"    Original: {txn['original_value']}")
        print(f"    New: {txn['new_value']}")
        print(f"    Timestamp: {txn['timestamp']}")

    if args.json:
        print("\n" + "=" * 70)
        print("JSON FORMAT")
        print("=" * 70)
        print(json.dumps(history, indent=2))

    return 0


def rollback(args) -> int:
    """Rollback all pending changes."""
    print("\n" + "=" * 70)
    print("ROLLBACK ALL CHANGES")
    print("=" * 70)

    spoofer = MacAddressSpoofer()

    print("\nRolling back all changes...")
    result = spoofer.rollback_all_changes()

    print(f"\nRolled back: {result['rolled_back_count']}")
    print(f"Failed: {result['failed_count']}")
    print(f"Overall success: {result['success']}")

    if not result['success'] and result['failed_transactions']:
        print("\nFailed to rollback:")
        for txn in result['failed_transactions']:
            print(f"  - {txn['action']} on {txn['interface']}")

    return 0 if result['success'] else 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='MAC Address Spoofer - Cross-platform MAC spoofing with automatic rollback',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # List all network interfaces
  python mac_spoofer_cli.py list

  # Validate a MAC address
  python mac_spoofer_cli.py validate 00:25:86:12:34:56

  # Spoof MAC on interface
  python mac_spoofer_cli.py spoof eth0 00:25:86:12:34:56

  # Generate and spoof random MAC (realistic patterns)
  python mac_spoofer_cli.py random eth0

  # Generate realistic MAC addresses
  python mac_spoofer_cli.py generate -c 5

  # Show transaction history
  python mac_spoofer_cli.py history --json

  # Rollback all changes
  python mac_spoofer_cli.py rollback
        '''
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List command
    subparsers.add_parser('list', help='List network interfaces')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate MAC address')
    validate_parser.add_argument('mac', help='MAC address to validate')
    validate_parser.add_argument(
        '--strict',
        action='store_true',
        help='Strict validation (require known vendor)'
    )

    # Spoof command
    spoof_parser = subparsers.add_parser('spoof', help='Spoof MAC address')
    spoof_parser.add_argument('interface', help='Network interface name')
    spoof_parser.add_argument('mac', help='New MAC address')
    spoof_parser.add_argument(
        '--force',
        action='store_true',
        help='Skip validation checks'
    )
    spoof_parser.add_argument(
        '--no-auto-rollback',
        action='store_true',
        help='Disable automatic rollback on errors'
    )

    # Random MAC command
    random_parser = subparsers.add_parser('random', help='Spoof random MAC address')
    random_parser.add_argument('interface', help='Network interface name')
    random_parser.add_argument(
        '--no-realistic',
        dest='realistic',
        action='store_false',
        default=True,
        help='Generate random MAC (not from known vendors)'
    )
    random_parser.add_argument(
        '--no-auto-rollback',
        action='store_true',
        help='Disable automatic rollback on errors'
    )

    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate MAC addresses')
    gen_parser.add_argument(
        '-c', '--count',
        type=int,
        default=1,
        help='Number of MAC addresses to generate'
    )

    # History command
    hist_parser = subparsers.add_parser('history', help='Show transaction history')
    hist_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    # Rollback command
    subparsers.add_parser('rollback', help='Rollback all changes')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Dispatch to command handlers
    command_handlers = {
        'list': list_interfaces,
        'validate': validate_mac,
        'spoof': spoof_mac,
        'random': spoof_random_mac,
        'generate': generate_mac,
        'history': show_history,
        'rollback': rollback,
    }

    if not args.command:
        parser.print_help()
        return 0

    handler = command_handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
