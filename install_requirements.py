#!/usr/bin/env python3
"""
Installation script for MAC Address Spoofer prerequisites.
Validates Python version and required system components.
"""

import sys
import platform
import subprocess
from pathlib import Path


class InstallationValidator:
    """Validates and reports on installation requirements."""

    MIN_PYTHON_VERSION = (3, 7)
    REQUIRED_COMMANDS = {
        'Windows': ['wmic'],
        'Linux': ['ip', 'ethtool', 'sudo'],
        'Darwin': ['ifconfig', 'networksetup', 'sudo']
    }

    @staticmethod
    def check_python_version():
        """Check if Python version meets minimum requirement."""
        print("=" * 70)
        print("CHECKING PYTHON VERSION")
        print("=" * 70)

        current = sys.version_info[:2]
        required = InstallationValidator.MIN_PYTHON_VERSION

        version_str = f"{current[0]}.{current[1]}.{sys.version_info[2]}"
        required_str = f"{required[0]}.{required[1]}+"

        print(f"\nCurrent Python version: {version_str}")
        print(f"Required Python version: {required_str}")

        if current >= required:
            print("✓ Python version is compatible\n")
            return True
        else:
            print(f"✗ Python version is too old")
            print(f"  Please upgrade to Python 3.7 or later\n")
            return False

    @staticmethod
    def check_platform():
        """Check current platform."""
        print("=" * 70)
        print("CHECKING OPERATING SYSTEM")
        print("=" * 70)

        os_name = platform.system()
        os_release = platform.release()
        os_version = platform.version()

        print(f"\nOperating System: {os_name}")
        print(f"Release: {os_release}")
        print(f"Version: {os_version}")

        supported = ['Windows', 'Linux', 'Darwin']
        if os_name in supported:
            print(f"✓ {os_name} is supported\n")
            return True
        else:
            print(f"✗ {os_name} is not currently supported")
            print(f"  Supported platforms: {', '.join(supported)}\n")
            return False

    @staticmethod
    def check_required_commands():
        """Check for required system commands."""
        print("=" * 70)
        print("CHECKING REQUIRED SYSTEM COMMANDS")
        print("=" * 70)

        os_name = platform.system()
        required = InstallationValidator.REQUIRED_COMMANDS.get(os_name, [])

        if not required:
            print(f"\nNo specific commands required for {os_name}\n")
            return True

        print(f"\nRequired commands for {os_name}:")
        all_found = True

        for cmd in required:
            if InstallationValidator._command_exists(cmd):
                print(f"  ✓ {cmd}")
            else:
                print(f"  ✗ {cmd} - NOT FOUND")
                all_found = False

        if not all_found:
            print(f"\n⚠ Some required commands are missing.")
            print(f"  Installation instructions:")

            if os_name == 'Windows':
                print(f"  - WMI is included in Windows 10+")
                print(f"  - No additional installation needed for WMI")
            elif os_name == 'Linux':
                print(f"  - Ubuntu/Debian: sudo apt-get install iproute2 ethtool")
                print(f"  - Fedora/RHEL: sudo dnf install iproute ethtool")
                print(f"  - Arch: sudo pacman -S iproute2 ethtool")
            elif os_name == 'Darwin':
                print(f"  - macOS tools are built-in")
                print(f"  - No additional installation needed")

            print()
            return all_found

        print()
        return True

    @staticmethod
    def check_dependencies():
        """Check for Python dependencies."""
        print("=" * 70)
        print("CHECKING PYTHON DEPENDENCIES")
        print("=" * 70)

        print("\nPython Standard Library modules (always available):")
        stdlib_modules = [
            'subprocess', 'logging', 're', 'json', 'typing',
            'dataclasses', 'abc', 'unittest', 'argparse'
        ]

        all_found = True
        for module in stdlib_modules:
            try:
                __import__(module)
                print(f"  ✓ {module}")
            except ImportError:
                print(f"  ✗ {module}")
                all_found = False

        print("\n✓ No external dependencies required!")
        print("  The tool uses only Python standard library (Python 3.7+)\n")
        return all_found

    @staticmethod
    def check_admin_privileges():
        """Check if user has administrative privileges."""
        print("=" * 70)
        print("CHECKING ADMINISTRATIVE PRIVILEGES")
        print("=" * 70)

        os_name = platform.system()

        if os_name == 'Windows':
            try:
                import ctypes
                is_admin = ctypes.windll.shell.IsUserAnAdmin()
                status = "✓" if is_admin else "ℹ"
                print(f"\n{status} Administrator privileges: {'Present' if is_admin else 'Not Present'}")
                print("  Note: Admin privileges are REQUIRED for actual MAC spoofing")
                print("  Validation and generation commands work without admin access\n")
                return True
            except Exception as e:
                print(f"\n⚠ Could not check admin status: {e}")
                print("  Note: Admin privileges are required for MAC spoofing\n")
                return True
        else:
            # Linux/macOS
            uid = subprocess.run(['id', '-u'], capture_output=True, text=True).stdout.strip()
            is_root = uid == '0'
            status = "✓" if is_root else "ℹ"
            print(f"\n{status} Root/sudo privileges: {'Present' if is_root else 'Not Present'}")
            print("  Note: Root/sudo privileges are REQUIRED for actual MAC spoofing")
            print("  Validation and generation commands work without root access\n")
            return True

    @staticmethod
    def _command_exists(command):
        """Check if a command exists in PATH."""
        try:
            if platform.system() == 'Windows':
                result = subprocess.run(
                    ['where', command],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
            else:
                result = subprocess.run(
                    ['which', command],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def check_test_framework():
        """Check if unittest is available."""
        print("=" * 70)
        print("CHECKING TEST FRAMEWORK")
        print("=" * 70)

        try:
            import unittest
            print("\n✓ unittest is available")
            print("  Run tests with: python tests.py\n")
            return True
        except ImportError:
            print("\n✗ unittest is not available")
            print("  This is unusual - unittest is part of Python stdlib\n")
            return False

    @staticmethod
    def run_all_checks():
        """Run all installation checks."""
        print("\n")
        print("╔" + "=" * 68 + "╗")
        print("║" + " " * 15 + "MAC ADDRESS SPOOFER - INSTALLATION CHECK" + " " * 12 + "║")
        print("║" + " " * 18 + "Developer: MrAmirRezaie" + " " * 25 + "║")
        print("╚" + "=" * 68 + "╝")
        print()

        results = {
            "Python Version": InstallationValidator.check_python_version(),
            "Operating System": InstallationValidator.check_platform(),
            "System Commands": InstallationValidator.check_required_commands(),
            "Python Dependencies": InstallationValidator.check_dependencies(),
            "Test Framework": InstallationValidator.check_test_framework(),
            "Administrative Privileges": InstallationValidator.check_admin_privileges(),
        }

        print("=" * 70)
        print("INSTALLATION CHECK SUMMARY")
        print("=" * 70)
        print()

        for check, result in results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {check}")

        critical_passed = all([
            results["Python Version"],
            results["Operating System"],
            results["Python Dependencies"]
        ])

        nice_to_have_passed = all([
            results["System Commands"],
            results["Test Framework"],
            results["Administrative Privileges"]
        ])

        print()
        print("=" * 70)
        if critical_passed:
            print("✓ INSTALLATION CHECK PASSED")
            print()
            print("The tool is ready to use!")
            print()
            print("Quick start:")
            print("  1. List interfaces:     python mac_spoofer_cli.py list")
            print("  2. Validate MAC:        python mac_spoofer_cli.py validate <MAC>")
            print("  3. Generate MACs:       python mac_spoofer_cli.py generate -c 5")
            print("  4. Run tests:           python tests.py")
            print()

            if not nice_to_have_passed:
                print("⚠ Some optional components are missing, but the tool will still work.")

            print("=" * 70)
            return 0
        else:
            print("✗ INSTALLATION CHECK FAILED")
            print()
            print("Please fix the issues above and try again.")
            print("=" * 70)
            return 1


def main():
    """Main entry point."""
    try:
        exit_code = InstallationValidator.run_all_checks()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInstallation check cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error during installation check: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
