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

- Cross-platform support: Windows, Linux, macOS
- Real vendor OUI pattern matching (16+ vendors)
- RFC 5342-compliant MAC validation and realistic MAC generation
- Transaction-based changes with automatic rollback on errors
- Pre/post verification of applied changes
- CLI and Python API for automation and scripting

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

- `list` — enumerate detected network interfaces.
- `validate <mac>` — validate MAC format, vendor, and flags.
- `generate` — generate realistic MAC(s) from real OUIs.
- `spoof` — set a provided MAC on an interface (requires admin).
- `random` — generate and apply a realistic random MAC.
- `history` — display transaction history.
- `rollback` — run rollback callbacks for a transaction.

Examples:

```bash
python mac_spoofer_cli.py spoof --interface eth0 --mac 00:25:86:12:34:56 --verify
python mac_spoofer_cli.py generate -c 5 --vendor Intel
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
