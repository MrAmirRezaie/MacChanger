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
from config_manager import ConfigManager
from mac_history import MacHistory
from scheduler import Scheduler, ScheduleFrequency
from interface_filter import InterfaceFilter


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


def manage_profiles(args) -> int:
    """Manage MAC address profiles."""
    print("\n" + "=" * 70)
    print("PROFILE MANAGEMENT")
    print("=" * 70)

    config_mgr = ConfigManager()

    if args.profile_action == "list":
        print("\nAvailable Profiles:")
        profiles = config_mgr.list_profiles()
        if not profiles:
            print("  No profiles found.")
        else:
            for p in profiles:
                print(f"\n  {p['name']}")
                if p['description']:
                    print(f"    Description: {p['description']}")
                print(f"    Interfaces: {p['interface_count']}")
                print(f"    Created: {p['created_at']}")
        return 0

    elif args.profile_action == "create":
        if not args.name:
            print("Profile name is required")
            return 1
        profile = config_mgr.create_profile(args.name, args.description or "")
        if profile:
            print(f"✓ Profile created: {args.name}")
            return 0
        else:
            print(f"✗ Failed to create profile: {args.name}")
            return 1

    elif args.profile_action == "delete":
        if not args.name:
            print("Profile name is required")
            return 1
        if config_mgr.delete_profile(args.name):
            print(f"✓ Profile deleted: {args.name}")
            return 0
        else:
            print(f"✗ Failed to delete profile: {args.name}")
            return 1

    elif args.profile_action == "show":
        if not args.name:
            print("Profile name is required")
            return 1
        profile = config_mgr.get_profile(args.name)
        if not profile:
            print(f"Profile '{args.name}' not found")
            return 1
        print(f"\nProfile: {profile.name}")
        print(f"Description: {profile.description}")
        print(f"Interfaces: {len(profile.interfaces)}")
        for iface, mac in profile.interfaces.items():
            print(f"  - {iface}: {mac}")
        return 0

    return 0


def manage_mac_history(args) -> int:
    """Manage MAC address history."""
    print("\n" + "=" * 70)
    print("MAC ADDRESS HISTORY")
    print("=" * 70)

    history_mgr = MacHistory()

    if args.history_action == "list":
        interface = args.interface if hasattr(args, 'interface') and args.interface else None
        entries = history_mgr.list_entries(interface=interface, limit=20)
        if not entries:
            print("\nNo history entries found.")
        else:
            print(f"\nLast 20 entries:")
            for entry in entries:
                print(f"\n  {entry['timestamp']}")
                print(f"    Interface: {entry['interface']}")
                print(f"    MAC: {entry['mac_address']}")
                print(f"    Action: {entry['action']} ({entry['status']})")
                if entry['notes']:
                    print(f"    Notes: {entry['notes']}")
        return 0

    elif args.history_action == "clear":
        interface = args.interface if hasattr(args, 'interface') and args.interface else None
        cleared = history_mgr.clear_history(interface)
        print(f"✓ Cleared {cleared} history entries")
        return 0

    elif args.history_action == "stats":
        stats = history_mgr.get_statistics()
        print("\nMAC History Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return 0

    return 0


def manage_scheduler(args) -> int:
    """Manage task scheduling."""
    print("\n" + "=" * 70)
    print("TASK SCHEDULER")
    print("=" * 70)

    scheduler = Scheduler()

    if args.scheduler_action == "list":
        print("\nScheduled Tasks:")
        tasks = scheduler.list_tasks()
        if not tasks:
            print("  No tasks scheduled.")
        else:
            for task in tasks:
                status = "✓" if task['enabled'] else "✗"
                print(f"\n  {status} {task['name']}")
                print(f"     Interface: {task['interface']}")
                print(f"     Action: {task['action']}")
                print(f"     Frequency: {task['frequency']}")
                print(f"     Next run: {task['next_run']}")
        return 0

    elif args.scheduler_action == "create":
        if not all([args.name, args.interface, args.action, args.frequency]):
            print("name, interface, action, and frequency are required")
            return 1

        try:
            freq = ScheduleFrequency(args.frequency)
        except ValueError:
            print(f"Invalid frequency: {args.frequency}")
            return 1

        task = scheduler.create_task(
            args.name,
            args.interface,
            args.action,
            freq,
            description=args.description or ""
        )

        if task:
            print(f"✓ Task created: {args.name}")
            return 0
        else:
            print(f"✗ Failed to create task")
            return 1

    elif args.scheduler_action == "delete":
        if not args.name:
            print("Task name is required")
            return 1

        if scheduler.delete_task(args.name):
            print(f"✓ Task deleted: {args.name}")
            return 0
        else:
            print(f"✗ Failed to delete task")
            return 1

    elif args.scheduler_action == "enable":
        if not args.name:
            print("Task name is required")
            return 1

        if scheduler.enable_task(args.name):
            print(f"✓ Task enabled: {args.name}")
            return 0
        else:
            print(f"✗ Failed to enable task")
            return 1

    elif args.scheduler_action == "disable":
        if not args.name:
            print("Task name is required")
            return 1

        if scheduler.disable_task(args.name):
            print(f"✓ Task disabled: {args.name}")
            return 0
        else:
            print(f"✗ Failed to disable task")
            return 1

    return 0


def filter_interfaces(args) -> int:
    """Filter and list network interfaces with advanced options."""
    print("\n" + "=" * 70)
    print("NETWORK INTERFACE SEARCH")
    print("=" * 70)

    spoofer = MacAddressSpoofer()
    interfaces = spoofer.get_available_interfaces()

    # Convert dict list to NetworkInterface objects
    from platform_handlers import NetworkInterface
    net_interfaces = [
        NetworkInterface(
            name=iface['name'],
            mac_address=iface['mac_address'],
            status=iface['status'],
            driver=iface['driver']
        )
        for iface in interfaces
    ]

    # Apply filters
    filters = {}
    if args.status:
        filters['status'] = args.status
    if args.driver:
        filters['driver'] = args.driver
    if args.active_only:
        filters['active_only'] = True

    filtered = InterfaceFilter.apply_filters(net_interfaces, filters)

    # Apply search if keyword provided
    if args.search:
        filtered = InterfaceFilter.search(filtered, args.search)

    # Apply sorting
    if args.sort_by:
        filtered = InterfaceFilter.sort_by_field(
            filtered, args.sort_by, reverse=args.sort_reverse
        )

    print(f"\nFound {len(filtered)} matching interface(s):\n")
    print(InterfaceFilter.to_table(filtered))

    return 0


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

    # Profile management
    profile_parser = subparsers.add_parser('profile', help='Manage MAC profiles')
    profile_subparsers = profile_parser.add_subparsers(dest='profile_action', required=True)
    profile_subparsers.add_parser('list', help='List all profiles')
    create_profile = profile_subparsers.add_parser('create', help='Create new profile')
    create_profile.add_argument('--name', required=True, help='Profile name')
    create_profile.add_argument('--description', help='Profile description')
    delete_profile = profile_subparsers.add_parser('delete', help='Delete profile')
    delete_profile.add_argument('--name', required=True, help='Profile name')
    show_profile = profile_subparsers.add_parser('show', help='Show profile details')
    show_profile.add_argument('--name', required=True, help='Profile name')

    # MAC History
    history_parser = subparsers.add_parser('mac-history', help='Manage MAC address history')
    history_subparsers = history_parser.add_subparsers(dest='history_action', required=True)
    history_subparsers.add_parser('list', help='List MAC history')
    history_subparsers.add_parser('stats', help='Show history statistics')
    clear_history = history_subparsers.add_parser('clear', help='Clear history')
    clear_history.add_argument('--interface', help='Clear history for specific interface')

    # Scheduler
    scheduler_parser = subparsers.add_parser('schedule', help='Manage task scheduling')
    scheduler_subparsers = scheduler_parser.add_subparsers(dest='scheduler_action', required=True)
    scheduler_subparsers.add_parser('list', help='List scheduled tasks')
    create_task = scheduler_subparsers.add_parser('create', help='Create scheduled task')
    create_task.add_argument('--name', required=True, help='Task name')
    create_task.add_argument('--interface', required=True, help='Target interface')
    create_task.add_argument('--action', required=True, help='Action to perform')
    create_task.add_argument('--frequency', required=True, help='Frequency (once, hourly, daily, weekly)')
    create_task.add_argument('--description', help='Task description')
    delete_task = scheduler_subparsers.add_parser('delete', help='Delete scheduled task')
    delete_task.add_argument('--name', required=True, help='Task name')
    enable_task = scheduler_subparsers.add_parser('enable', help='Enable scheduled task')
    enable_task.add_argument('--name', required=True, help='Task name')
    disable_task = scheduler_subparsers.add_parser('disable', help='Disable scheduled task')
    disable_task.add_argument('--name', required=True, help='Task name')

    # Interface filter/search
    filter_parser = subparsers.add_parser('search', help='Search and filter interfaces')
    filter_parser.add_argument('--search', help='Keyword to search for')
    filter_parser.add_argument('--status', help='Filter by status (up/down)')
    filter_parser.add_argument('--driver', help='Filter by driver')
    filter_parser.add_argument('--active-only', action='store_true', help='Show only active interfaces')
    filter_parser.add_argument('--sort-by', help='Sort by field (name, mac, status, ip)')
    filter_parser.add_argument('--sort-reverse', action='store_true', help='Reverse sort order')

    # Parse arguments
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
        'profile': manage_profiles,
        'mac-history': manage_mac_history,
        'schedule': manage_scheduler,
        'search': filter_interfaces,
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
