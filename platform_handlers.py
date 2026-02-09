"""
Platform-specific handlers for MAC address spoofing.
Supports Windows, Linux, and macOS.
"""

import subprocess
import logging
import re
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NetworkInterface:
    """Represents a network interface with extended information."""
    name: str
    mac_address: str
    status: str
    driver: Optional[str] = None
    description: Optional[str] = None
    ip_address: Optional[str] = None
    netmask: Optional[str] = None
    ipv6_address: Optional[str] = None
    mtu: Optional[int] = None
    speed: Optional[str] = None  # e.g., "1000 Mb/s"
    interface_type: Optional[str] = None  # e.g., "Ethernet", "Wireless"
    vendor: Optional[str] = None  # OUI vendor name

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'mac_address': self.mac_address,
            'status': self.status,
            'ip_address': self.ip_address,
            'netmask': self.netmask,
            'ipv6_address': self.ipv6_address,
            'mtu': self.mtu,
            'speed': self.speed,
            'interface_type': self.interface_type,
            'driver': self.driver,
            'description': self.description,
            'vendor': self.vendor
        }


class PlatformHandler(ABC):
    """Abstract base class for platform-specific handlers."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def get_interfaces(self) -> List[NetworkInterface]:
        """Get list of network interfaces."""
        pass

    @abstractmethod
    def get_mac_address(self, interface: str) -> Optional[str]:
        """Get current MAC address of an interface."""
        pass

    @abstractmethod
    def set_mac_address(self, interface: str, mac_address: str) -> bool:
        """Set MAC address of an interface."""
        pass

    @abstractmethod
    def get_driver_name(self, interface: str) -> Optional[str]:
        """Get network driver name."""
        pass

    @abstractmethod
    def spoof_driver_info(self, interface: str, driver_name: str) -> bool:
        """Spoof driver information."""
        pass

    def get_ip_address(self, interface: str) -> Optional[str]:
        """Get IP address of an interface. Override in subclass for platform-specific implementation."""
        return None

    def get_ipv6_address(self, interface: str) -> Optional[str]:
        """Get IPv6 address of an interface. Override in subclass for platform-specific implementation."""
        return None

    def get_netmask(self, interface: str) -> Optional[str]:
        """Get netmask of an interface. Override in subclass for platform-specific implementation."""
        return None

    def get_mtu(self, interface: str) -> Optional[int]:
        """Get MTU of an interface. Override in subclass for platform-specific implementation."""
        return None

    def get_interface_type(self, interface: str) -> Optional[str]:
        """Get type of interface (Ethernet, Wireless, etc.)."""
        return None

    def get_interface_details(self, interface: str) -> Dict[str, Optional[str]]:
        """Get detailed information about an interface."""
        return {
            'ip_address': self.get_ip_address(interface),
            'ipv6_address': self.get_ipv6_address(interface),
            'netmask': self.get_netmask(interface),
            'mtu': self.get_mtu(interface),
            'type': self.get_interface_type(interface),
            'driver': self.get_driver_name(interface)
        }

    def run_command(
        self, command: str, admin: bool = False
    ) -> Tuple[bool, str, str]:
        """
        Run a system command safely.

        Returns:
            (success, stdout, stderr)
        """
        try:
            if admin and self.__class__.__name__ == "WindowsHandler":
                # On Windows, prepend elevation if needed
                command = f'powershell -Command "Start-Process cmd -ArgumentList /c,{repr(command)} -Verb RunAs"'

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timeout: {command}")
            return False, "", "Command execution timed out"
        except Exception as e:
            self.logger.error(f"Error running command: {e}")
            return False, "", str(e)


class WindowsHandler(PlatformHandler):
    """Handler for Windows platform."""

    def get_interfaces(self) -> List[NetworkInterface]:
        """Get network interfaces using ipconfig and wmic."""
        interfaces = []

        # Get adapters using wmic
        success, stdout, _ = self.run_command(
            'wmic nic where "AdapterType=\'Ethernet\' OR AdapterType=\'Wireless\'" Get name,MACAddress,NetEnabled /format:csv'
        )

        if success:
            lines = stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 3:
                        name = parts[0]
                        mac = parts[1]
                        enabled = parts[2] == 'TRUE'

                        # Get description
                        success, stdout, _ = self.run_command(
                            f'wmic nic where name="{name}" Get description /format:list'
                        )
                        description = None
                        if success and 'description=' in stdout:
                            description = stdout.split('description=')[1].strip()

                        interfaces.append(NetworkInterface(
                            name=name,
                            mac_address=mac if mac else "N/A",
                            status="up" if enabled else "down",
                            description=description
                        ))

        return interfaces

    def get_mac_address(self, interface: str) -> Optional[str]:
        """Get MAC address from adapter."""
        success, stdout, _ = self.run_command(
            f'wmic nic where name="{interface}" Get MACAddress /format:list'
        )

        if success and 'MACAddress=' in stdout:
            mac = stdout.split('MACAddress=')[1].strip()
            # Convert to standard format with colons
            mac = ":".join(mac[i:i+2] for i in range(0, len(mac), 2))
            return mac
        return None

    def set_mac_address(self, interface: str, mac_address: str) -> bool:
        """
        Set MAC address using registry modification.
        Requires admin privileges.
        """
        try:
            # Get the network adapter GUID
            success, stdout, _ = self.run_command(
                f'Get-NetAdapter -Name "{interface}" |  Select-Object -ExpandProperty InterfaceGuid',
            )

            if not success or not stdout:
                self.logger.error(f"Could not get GUID for interface {interface}")
                return False

            guid = stdout.strip().strip('{}')

            # Prepare MAC address for registry (remove colons)
            reg_mac = mac_address.replace(":", "").upper()

            # Registry path for network adapter settings
            reg_path = (
                f"HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Class\\"
                f"{{4D36E972-E325-11CE-BFC1-08002BE10318}}"
            )

            # Note: This requires admin privileges and may need different approaches
            # depending on driver support
            ps_command = (
                f'powershell -Command "Set-ItemProperty -Path '
                f"'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Class\\"
                f'{{4D36E972-E325-11CE-BFC1-08002BE10318}}\\*\\NetworkAddress\' '
                f'-Name \'NetworkAddress\' -Value \'{reg_mac}\' -Force"'
            )

            success, _, stderr = self.run_command(ps_command)

            if success:
                self.logger.info(f"MAC address changed to {mac_address} (registry)")
                # Sometimes requires restart or NIC reset
                # Try to restart the adapter
                self.run_command(f'Restart-NetAdapter -Name "{interface}" -Confirm:$false')
                return True
            else:
                self.logger.error(f"Failed to set MAC: {stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error setting MAC address: {e}")
            return False

    def get_driver_name(self, interface: str) -> Optional[str]:
        """Get driver name for interface."""
        success, stdout, _ = self.run_command(
            f'Get-NetAdapter -Name "{interface}" | Select-Object -ExpandProperty DriverFileName'
        )

        if success and stdout:
            return stdout.strip()
        return None

    def spoof_driver_info(self, interface: str, driver_name: str) -> bool:
        """Spoof driver information (Windows)."""
        self.logger.warning("Driver spoofing on Windows requires driver-level modification")
        return False


class LinuxHandler(PlatformHandler):
    """Handler for Linux platform."""

    def get_interfaces(self) -> List[NetworkInterface]:
        """Get network interfaces using ip command."""
        interfaces = []

        success, stdout, _ = self.run_command("ip link show")
        if not success:
            return interfaces

        lines = stdout.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            # Parse "1: lo: <LOOPBACK,UP,LOWER_UP>..."
            match = re.match(r'^(\d+):\s+(\S+):\s+<([^>]+)>', line)
            if match:
                name = match.group(2)
                flags = match.group(3)

                # Get MAC address from next lines
                mac = "N/A"
                i += 1
                if i < len(lines):
                    link_match = re.search(r'link/ether\s+([0-9a-f:]+)', lines[i])
                    if link_match:
                        mac = link_match.group(1)

                status = "up" if "UP" in flags else "down"

                interfaces.append(NetworkInterface(
                    name=name,
                    mac_address=mac,
                    status=status
                ))

            i += 1

        return interfaces

    def get_mac_address(self, interface: str) -> Optional[str]:
        """Get MAC address from interface."""
        success, stdout, _ = self.run_command(f"ip link show {interface}")

        if success:
            match = re.search(r'link/ether\s+([0-9a-f:]+)', stdout)
            if match:
                return match.group(1)
        return None

    def set_mac_address(self, interface: str, mac_address: str) -> bool:
        """Set MAC address on Linux."""
        try:
            # Bring interface down
            success, _, stderr = self.run_command(f"sudo ip link set {interface} down")
            if not success:
                self.logger.warning(f"Could not bring down interface: {stderr}")

            # Change MAC address
            success, _, stderr = self.run_command(
                f"sudo ip link set {interface} address {mac_address}"
            )

            if success:
                self.logger.info(f"Set MAC on {interface} to {mac_address}")
            else:
                self.logger.error(f"Failed to set MAC: {stderr}")
                # Bring interface back up even on failure
                self.run_command(f"sudo ip link set {interface} up")
                return False

            # Bring interface back up
            success2, _, _ = self.run_command(f"sudo ip link set {interface} up")
            return success and success2

        except Exception as e:
            self.logger.error(f"Error setting MAC address: {e}")
            return False

    def get_driver_name(self, interface: str) -> Optional[str]:
        """Get driver name for interface."""
        success, stdout, _ = self.run_command(f"ethtool -i {interface}")

        if success and "driver:" in stdout:
            for line in stdout.split('\n'):
                if line.startswith("driver:"):
                    return line.split(":", 1)[1].strip()
        return None

    def spoof_driver_info(self, interface: str, driver_name: str) -> bool:
        """Spoof driver information (Linux)."""
        self.logger.warning("Driver spoofing on Linux not supported without kernel modules")
        return False


class MacOSHandler(PlatformHandler):
    """Handler for macOS platform."""

    def get_interfaces(self) -> List[NetworkInterface]:
        """Get network interfaces using ifconfig and networksetup."""
        interfaces = []

        success, stdout, _ = self.run_command("ifconfig")
        if not success:
            return interfaces

        lines = stdout.split('\n')
        current_interface = None

        for line in lines:
            # Match interface line: "en0: flags=..."
            match = re.match(r'^([a-z0-9]+):\s+flags=', line)
            if match:
                current_interface = match.group(1)
                interfaces.append(NetworkInterface(
                    name=current_interface,
                    mac_address="N/A",
                    status="up"
                ))
            # Match MAC address line
            elif current_interface and "ether " in line:
                match = re.search(r'ether\s+([0-9a-f:]+)', line)
                if match:
                    interfaces[-1].mac_address = match.group(1)

        return interfaces

    def get_mac_address(self, interface: str) -> Optional[str]:
        """Get MAC address from interface."""
        success, stdout, _ = self.run_command(f"ifconfig {interface}")

        if success:
            match = re.search(r'ether\s+([0-9a-f:]+)', stdout)
            if match:
                return match.group(1)
        return None

    def set_mac_address(self, interface: str, mac_address: str) -> bool:
        """Set MAC address on macOS."""
        try:
            # Create a dummy address first
            success, _, _ = self.run_command(
                f"sudo ifconfig {interface} ether {mac_address}"
            )

            if success:
                self.logger.info(f"Set MAC on {interface} to {mac_address}")
                return True
            else:
                self.logger.error(f"Failed to set MAC on {interface}")
                return False

        except Exception as e:
            self.logger.error(f"Error setting MAC address: {e}")
            return False

    def get_driver_name(self, interface: str) -> Optional[str]:
        """Get driver name for interface."""
        success, stdout, _ = self.run_command(f"kextstat | grep -i {interface}")

        if success and stdout:
            return stdout.split()[0]
        return None

    def spoof_driver_info(self, interface: str, driver_name: str) -> bool:
        """Spoof driver information (macOS)."""
        self.logger.warning("Driver spoofing on macOS requires System Integrity Protection bypass")
        return False


def get_platform_handler() -> PlatformHandler:
    """Get the appropriate platform handler for the current OS."""
    import platform
    import sys

    os_name = platform.system().lower()
    logger = logging.getLogger(__name__)

    if os_name == 'windows':
        logger.info("Using Windows handler")
        return WindowsHandler()
    elif os_name == 'linux':
        logger.info("Using Linux handler")
        return LinuxHandler()
    elif os_name == 'darwin':
        logger.info("Using macOS handler")
        return MacOSHandler()
    else:
        raise RuntimeError(f"Unsupported platform: {os_name}")


def test_platform_handler():
    """Test platform handler."""
    print("=" * 60)
    print("Platform Handler Tests")
    print("=" * 60)

    logging.basicConfig(level=logging.INFO)

    handler = get_platform_handler()
    print(f"\nUsing handler: {handler.__class__.__name__}")

    print("\nAvailable network interfaces:")
    print("-" * 60)
    interfaces = handler.get_interfaces()
    for iface in interfaces:
        print(f"  {iface.name}: {iface.mac_address} ({iface.status})")
        if iface.description:
            print(f"    Description: {iface.description}")


if __name__ == "__main__":
    test_platform_handler()
