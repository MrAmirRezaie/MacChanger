# MAC Address Spoofer (MacChanger) 🔧

[![Python 3.7+](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%2B%20Restrictions-red)](./LICENSE)
[![Platform Support](https://img.shields.io/badge/platforms-Windows%20%7C%20Linux%20%7C%20macOS-brightgreen)](#platform-support)
[![Tests](https://img.shields.io/badge/tests-24%2F24%20passing-brightgreen)](./tests.py)

A professional-grade, cross-platform MAC address spoofing tool designed for network testing and security research. Features real vendor OUI pattern matching, automatic error detection and recovery, transaction-based rollback capabilities, and support for Windows, Linux, and macOS. Built with security, reliability, and ease of use in mind.

**Built by:** [MrAmirRezaie](https://github.com/MrAmirRezaie)

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Python API](#python-api)
- [Configuration Profiles](#configuration-profiles)
- [MAC Address History](#mac-address-history)
- [Task Scheduling](#task-scheduling)
- [Interface Filtering & Search](#interface-filtering--search)
- [Transaction & Rollback](#transaction--rollback)
- [Platform Notes](#platform-notes)
- [Warnings & Legal Notice](#warnings--legal-notice)
- [Troubleshooting](#troubleshooting)
- [Testing](#testing)
- [Contributing](#contributing)
- [License & Attribution](#license--attribution)
- [Contact](#contact)

---

## Features

- **Cross-platform support**: Windows, Linux, macOS
- **Real vendor OUI pattern matching**: 70+ vendor MACs for realistic randomization
- **RFC 5342-compliant MAC validation** and realistic MAC generation
- **Transaction-based changes** with automatic rollback on errors  
- **Pre/post verification** of applied changes with detailed reporting
- **CLI and Python API** for automation and scripting
- **Configuration Profiles**: Save and load MAC mappings for multiple interfaces
- **MAC History Database**: Track all MAC address changes with backup/recovery options
- **Advanced Interface Filtering**: Search and filter interfaces by name, status, vendor, driver, IP
- **Task Scheduling**: Schedule periodic MAC address randomization (hourly, daily, weekly, monthly, custom)
- **Extended Interface Information**: Retrieve IP addresses, MTU, network type, and more
- **Settings Management**: Persist configuration and preferences across sessions
- **Export/Import**: Backup and restore profiles, history, and schedules
- **Batch Operations**: Apply changes to multiple interfaces with atomic rollback on failure

---

## Prerequisites

- Python 3.7 or newer (3.12 recommended). The project uses only the Python standard library.
- Platform-specific utilities (for full functionality):
	- Windows: PowerShell and WMI access (some older helpers may use `wmic`)
	- Linux: `ip`, `ethtool`, and root/sudo privileges
	- macOS: `ifconfig` and sudo privileges
- Administrative privileges are required to actually change MAC addresses. Without them, the tool can validate and generate MACs but cannot apply them.

If you are unsure whether your system has required utilities, run:

```powershell
python install_requirements.py
```

---

## Installation

1. Clone the repository or download the source into a working folder.
2. (Optional) Create and activate a virtual environment:

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

3. No external packages required—this project uses the standard library only. Use `install_requirements.py` to validate your environment:

```bash
python install_requirements.py
```

---

## Quick Start

From the repository root, list network interfaces:

```bash
python mac_spoofer_cli.py list
```

Validate an existing MAC address:

```bash
python mac_spoofer_cli.py validate 00:25:86:12:34:56
```

Generate realistic MAC addresses (3 examples):

```bash
python mac_spoofer_cli.py generate -c 3
```

Spoof a specific interface (requires admin):

```bash
python mac_spoofer_cli.py spoof --interface Ethernet0 --mac 02:00:5e:10:00:00
```

Spoof a random realistic MAC for an interface:

```bash
python mac_spoofer_cli.py random --interface eth0
```

Show transaction history and committed changes:

```bash
python mac_spoofer_cli.py history
```

Rollback the last transaction:

```bash
python mac_spoofer_cli.py rollback
```

Use `-h` with any command for more details, or `--json` to get machine-readable output where supported.

---

## CLI Usage

Primary commands provided by `mac_spoofer_cli.py`:

**Core Commands:**
- `list` — enumerate detected network interfaces with details
- `validate <mac>` — validate MAC format, vendor, and flags
- `generate` — generate realistic MAC(s) from real OUIs
- `spoof <interface> <mac>` — set a provided MAC on an interface (requires admin)
- `random <interface>` — generate and apply a realistic random MAC
- `history` — display transaction history with optional JSON output
- `rollback` — run rollback callbacks for all transactions

**Profile Management:**
- `profile list` — list all saved MAC profiles
- `profile create --name <name> [--description <text>]` — create new profile
- `profile show --name <name>` — display profile details and mappings
- `profile delete --name <name>` — delete a profile

**MAC History:**
- `mac-history list [--interface <name>]` — display MAC address change history
- `mac-history stats` — show statistics about MAC history
- `mac-history clear [--interface <name>]` — clear history entries

**Task Scheduling:**
- `schedule list` — list all scheduled tasks
- `schedule create --name <name> --interface <iface> --action <action> --frequency <freq>` — create scheduled task
- `schedule enable --name <name>` — enable a scheduled task
- `schedule disable --name <name>` — disable a scheduled task
- `schedule delete --name <name>` — delete a scheduled task

**Interface Search & Filter:**
- `search [--search <keyword>] [--status <up|down>] [--driver <driver>] [--active-only] [--sort-by <field>]` — search and filter interfaces

**Examples:**

```bash
# List all active interfaces
python mac_spoofer_cli.py search --active-only

# Search for Intel interfaces
python mac_spoofer_cli.py search --search "intel"

# Create a profile for work network
python mac_spoofer_cli.py profile create --name work --description "Work network MACs"

# Schedule daily MAC randomization
python mac_spoofer_cli.py schedule create --name daily_spoof --interface eth0 --action spoof_random --frequency daily

# View MAC history statistics
python mac_spoofer_cli.py mac-history stats
```

---

## Python API

You can use the core engine from your scripts. Example:

```python
from mac_spoofer import MacAddressSpoofer

spoofer = MacAddressSpoofer(auto_rollback=True)
interfaces = spoofer.get_interfaces()
print(interfaces)

# Generate a realistic MAC and apply to first interface (requires admin)
new_mac = spoofer.generate_random_mac_for_interface(interfaces[0])
spoofer.spoof_mac_address(interfaces[0].name, new_mac)
```

Refer to the module docstrings for full API signatures: `mac_validator.py`, `transaction_manager.py`, `platform_handlers.py`, `mac_spoofer.py`.

---

## Configuration Profiles

Save and manage MAC address configurations for multiple interfaces as named profiles.

**Features:**
- Create named profiles with descriptions and tags
- Associate interfaces with specific MAC addresses
- Clone profiles for easy duplication
- Search profiles by name or tags
- Export/import profiles for backup and sharing

**Example Usage:**

```python
from config_manager import ConfigManager

config = ConfigManager()

# Create a profile
profile = config.create_profile("work", "Work network configuration")
profile.add_interface("eth0", "00:25:86:AA:BB:CC")
profile.add_interface("eth1", "52:54:00:AA:BB:CC")
config._save_profile(profile)

# List profiles
for p in config.list_profiles():
    print(f"{p['name']}: {p['interface_count']} interfaces")

# Clone a profile
config.clone_profile("work", "work_backup")
```

Profiles are stored in `~/.mac-spoofer/profiles/` as JSON files.

---

## MAC Address History

Keep a complete history of all MAC address changes with the ability to restore previous MACs.

**Features:**
- Automatic recording of all MAC spoofs and restores
- Original MAC detection and storage
- Search history by interface, MAC, or notes
- Restore previous MACs with one command
- Export/import history for archival
- Statistics on spoofing activity

**Example Usage:**

```python
from mac_history import MacHistory

history = MacHistory()

# Record a MAC change
history.record_spoof("eth0", "00:11:22:33:44:55", "00:25:86:AA:BB:CC")

# Get interface history
entries = history.get_interface_history("eth0")
for entry in entries:
    print(f"{entry['timestamp']}: {entry['mac_address']}")

# Restore original
original = history.restore_original_mac("eth0")
print(f"Original MAC: {original}")

# View statistics
stats = history.get_statistics()
print(f"Total MACs recorded: {stats['unique_macs']}")
```

History is stored in `~/.mac-spoofer/history/mac_history.json`.

---

## Task Scheduling

Schedule automatic MAC address randomization at regular intervals.

**Features:**
- Multiple frequency options: once, hourly, daily, weekly, monthly, custom
- Enable/disable tasks without deletion
- Track execution history with run counts
- Automatic task execution in background thread
- Search and filter scheduled tasks

**Supported Frequencies:**
- `once` — Run a single time
- `hourly` — Every hour
- `daily` — Every 24 hours
- `weekly` — Every 7 days
- `monthly` — Every 30 days
- `custom` — Custom interval in seconds

**Example Usage:**

```python
from scheduler import Scheduler, ScheduleFrequency

scheduler = Scheduler()

# Create a daily task
task = scheduler.create_task(
    name="daily_randomize",
    interface="eth0",
    action="spoof_random",
    frequency=ScheduleFrequency.DAILY,
    description="Randomize MAC daily at startup"
)

# List tasks
for task in scheduler.list_tasks(enabled_only=True):
    print(f"{task['name']}: {task['frequency']}")

# Start scheduler in background
scheduler.start(interval_seconds=60)

# Later...
scheduler.stop()
```

Scheduled tasks are stored in `~/.mac-spoofer/schedules/` as JSON files.

---

## Interface Filtering & Search

Advanced filtering, searching, and sorting of network interfaces.

**Filter Capabilities:**
- By name (exact or regex pattern)
- By status (up/down)
- By type (Ethernet/Wireless)
- By vendor name
- By driver
- By IP address presence
- Multiple filters combined

**Sort Options:**
- name, MAC address, status
- IP address, vendor, driver
- Interface type

**Example Usage:**

```python
from interface_filter import InterfaceFilter
from mac_spoofer import MacAddressSpoofer

spoofer = MacAddressSpoofer()
interfaces = spoofer.get_available_interfaces()

# Convert to NetworkInterface objects
from platform_handlers import NetworkInterface
net_ifaces = [
    NetworkInterface(
        name=i['name'],
        mac_address=i['mac_address'],
        status=i['status'],
        driver=i['driver']
    )
    for i in interfaces
]

# Filter active Ethernet interfaces
filters = {
    'status': 'up',
    'type': 'Ethernet'
}
filtered = InterfaceFilter.apply_filters(net_ifaces, filters)

# Search for Intel devices
intel_ifaces = InterfaceFilter.filter_by_vendor(net_ifaces, "Intel")

# Sort by MAC address
sorted_ifaces = InterfaceFilter.sort_by_field(net_ifaces, 'mac', reverse=False)

# Display as table
print(InterfaceFilter.to_table(filtered))
```

---

## Transaction & Rollback

All state-changing operations are performed inside transactions. Each action can register a rollback callback. If any step fails, the transaction manager runs registered callbacks in LIFO order to restore previous state.

Key points:

- Transactions are logged and can be inspected with the `history` command.
- Auto-rollback is enabled by default; you can disable it when orchestrating multi-interface operations if you handle recovery yourself.
- Rollbacks attempt best-effort restoration; some platform limitations may make full restoration impossible (see Troubleshooting).

---

## Platform Notes

- Windows: Administrative PowerShell is required to modify interface registry settings or use advanced WMI features. On modern Windows, `wmic` may be absent—PowerShell/WMI alternatives are used where available.
- Linux: Requires `ip` and usually `ethtool` for persistent driver-level spoofing. Some distributions may block MAC changes on certain interfaces (e.g., managed by NetworkManager); stop network manager or use its tools for persistent changes.
- macOS: `ifconfig` is used for on-the-fly changes. System Integrity Protection (SIP) and Apple-managed drivers can interfere with persistent changes.

Always test in a controlled environment first.

---

## Warnings & Legal Notice

- This tool can disrupt network connectivity. Use only on systems and networks you own or are explicitly authorized to test.
- Unauthorized MAC spoofing may violate local laws, organizational policies, or service agreements.
- The included `LICENSE` contains additional ethical and usage restrictions. By using this software you agree to follow those terms.
- The author is not responsible for misuse. Use responsibly and ethically.

If you need explicit exceptions for legitimate security research, obtain written authorization before running tests on third-party networks.

---

## Troubleshooting

- "Permission denied" or inability to apply MAC: run the CLI from an elevated shell (Administrator on Windows, `sudo` on Linux/macOS).
- Missing tools (e.g., `ethtool`, `ip`): install via your package manager (apt, yum, brew).
- After spoofing, some network stacks cache the hardware address—restarting the interface or OS may be required.
- If a change fails halfway through a bulk operation, the transaction manager attempts rollback; check `history` and `logs` for details.

If you need more help, open an issue using the provided templates in `.github/ISSUE_TEMPLATE/`.

---

## Testing

Run the full unit test suite to verify local functionality (no external dependencies required):

```bash
python tests.py
```

All tests should pass in a healthy environment (24/24 as provided).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines, code style, and testing requirements.

---

## License & Attribution

This project is distributed under the terms in the `LICENSE` file in this repository. The `LICENSE` includes additional restrictions and ethical use requirements—read it before use.

If you reuse or redistribute components, please attribute the original author: `MrAmirRezaie`.

---

## Contact

Project author: [MrAmirRezaie](https://github.com/MrAmirRezaie)

For security issues, follow the policy in `SECURITY.md` and use the responsible disclosure path described there.

---

Thank you for using MacChanger. Use responsibly.
