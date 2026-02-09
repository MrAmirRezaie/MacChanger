"""
Interface Filter - Provides filtering and search capabilities for network interfaces.
"""

import logging
import re
from typing import List, Dict, Optional, Any, Callable
from platform_handlers import NetworkInterface


class InterfaceFilter:
    """Provides advanced filtering and search for network interfaces."""

    def __init__(self):
        """Initialize interface filter."""
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def filter_by_name(
        interfaces: List[NetworkInterface],
        pattern: str,
        regex: bool = False
    ) -> List[NetworkInterface]:
        """
        Filter interfaces by name.

        Args:
            interfaces: List of network interfaces
            pattern: Name pattern to match
            regex: If True, treat pattern as regex

        Returns:
            Filtered list of interfaces
        """
        if not pattern:
            return interfaces

        result = []

        if regex:
            try:
                compiled_pattern = re.compile(pattern, re.IGNORECASE)
                result = [i for i in interfaces if compiled_pattern.search(i.name)]
            except re.error as e:
                logging.error(f"Invalid regex pattern: {e}")
                return []
        else:
            result = [i for i in interfaces if pattern.lower() in i.name.lower()]

        return result

    @staticmethod
    def filter_by_status(
        interfaces: List[NetworkInterface],
        status: str
    ) -> List[NetworkInterface]:
        """
        Filter interfaces by status (up/down/online/offline).

        Args:
            interfaces: List of network interfaces
            status: Status to filter by

        Returns:
            Filtered list of interfaces
        """
        status_lower = status.lower()
        return [
            i for i in interfaces
            if status_lower in i.status.lower()
        ]

    @staticmethod
    def filter_by_type(
        interfaces: List[NetworkInterface],
        interface_type: str
    ) -> List[NetworkInterface]:
        """
        Filter interfaces by type (Ethernet, Wireless, etc.).

        Args:
            interfaces: List of network interfaces
            interface_type: Type to filter by

        Returns:
            Filtered list of interfaces
        """
        type_lower = interface_type.lower()
        return [
            i for i in interfaces
            if i.interface_type and type_lower in i.interface_type.lower()
        ]

    @staticmethod
    def filter_by_vendor(
        interfaces: List[NetworkInterface],
        vendor_pattern: str
    ) -> List[NetworkInterface]:
        """
        Filter interfaces by vendor name.

        Args:
            interfaces: List of network interfaces
            vendor_pattern: Vendor pattern to match

        Returns:
            Filtered list of interfaces
        """
        vendor_lower = vendor_pattern.lower()
        return [
            i for i in interfaces
            if i.vendor and vendor_lower in i.vendor.lower()
        ]

    @staticmethod
    def filter_by_driver(
        interfaces: List[NetworkInterface],
        driver_pattern: str
    ) -> List[NetworkInterface]:
        """
        Filter interfaces by driver name.

        Args:
            interfaces: List of network interfaces
            driver_pattern: Driver pattern to match

        Returns:
            Filtered list of interfaces
        """
        driver_lower = driver_pattern.lower()
        return [
            i for i in interfaces
            if i.driver and driver_lower in i.driver.lower()
        ]

    @staticmethod
    def filter_has_ip(interfaces: List[NetworkInterface]) -> List[NetworkInterface]:
        """Filter interfaces that have an IP address."""
        return [i for i in interfaces if i.ip_address]

    @staticmethod
    def filter_no_ip(interfaces: List[NetworkInterface]) -> List[NetworkInterface]:
        """Filter interfaces that don't have an IP address."""
        return [i for i in interfaces if not i.ip_address]

    @staticmethod
    def filter_active(interfaces: List[NetworkInterface]) -> List[NetworkInterface]:
        """Filter only active (up) interfaces."""
        return [i for i in interfaces if 'up' in i.status.lower()]

    @staticmethod
    def filter_inactive(interfaces: List[NetworkInterface]) -> List[NetworkInterface]:
        """Filter only inactive (down) interfaces."""
        return [i for i in interfaces if 'down' in i.status.lower()]

    @staticmethod
    def search(
        interfaces: List[NetworkInterface],
        keyword: str
    ) -> List[NetworkInterface]:
        """
        Search interfaces by any field.

        Args:
            interfaces: List of network interfaces
            keyword: Keyword to search for

        Returns:
            Filtered list of interfaces
        """
        keyword_lower = keyword.lower()
        result = []

        for iface in interfaces:
            if any([
                keyword_lower in iface.name.lower(),
                keyword_lower in iface.mac_address.lower(),
                keyword_lower in iface.status.lower(),
                iface.ip_address and keyword_lower in iface.ip_address.lower(),
                iface.vendor and keyword_lower in iface.vendor.lower(),
                iface.driver and keyword_lower in iface.driver.lower(),
                iface.description and keyword_lower in iface.description.lower(),
            ]):
                result.append(iface)

        return result

    @staticmethod
    def filter_duplicate_macs(
        interfaces: List[NetworkInterface]
    ) -> Dict[str, List[NetworkInterface]]:
        """
        Find interfaces with duplicate MAC addresses.

        Args:
            interfaces: List of network interfaces

        Returns:
            Dict mapping MAC address to list of interfaces with that MAC
        """
        mac_map: Dict[str, List[NetworkInterface]] = {}

        for iface in interfaces:
            mac = iface.mac_address
            if mac not in mac_map:
                mac_map[mac] = []
            mac_map[mac].append(iface)

        # Return only MACs with duplicates
        return {mac: ifaces for mac, ifaces in mac_map.items() if len(ifaces) > 1}

    @staticmethod
    def apply_filters(
        interfaces: List[NetworkInterface],
        filters: Dict[str, Any]
    ) -> List[NetworkInterface]:
        """
        Apply multiple filters at once.

        Args:
            interfaces: List of network interfaces
            filters: Dict of filter_name -> value

        Returns:
            Filtered list of interfaces
        """
        result = interfaces

        if 'name' in filters:
            result = InterfaceFilter.filter_by_name(
                result,
                filters['name'],
                filters.get('name_regex', False)
            )

        if 'status' in filters:
            result = InterfaceFilter.filter_by_status(result, filters['status'])

        if 'type' in filters:
            result = InterfaceFilter.filter_by_type(result, filters['type'])

        if 'vendor' in filters:
            result = InterfaceFilter.filter_by_vendor(result, filters['vendor'])

        if 'driver' in filters:
            result = InterfaceFilter.filter_by_driver(result, filters['driver'])

        if filters.get('has_ip'):
            result = InterfaceFilter.filter_has_ip(result)

        if filters.get('no_ip'):
            result = InterfaceFilter.filter_no_ip(result)

        if filters.get('active_only'):
            result = InterfaceFilter.filter_active(result)

        if filters.get('inactive_only'):
            result = InterfaceFilter.filter_inactive(result)

        return result

    @staticmethod
    def sort_by_field(
        interfaces: List[NetworkInterface],
        field: str,
        reverse: bool = False
    ) -> List[NetworkInterface]:
        """
        Sort interfaces by a field.

        Args:
            interfaces: List of network interfaces
            field: Field name to sort by (name, mac_address, status, ip_address, etc.)
            reverse: If True, sort in descending order

        Returns:
            Sorted list of interfaces
        """
        field_lower = field.lower()

        def get_sort_key(iface: NetworkInterface) -> Any:
            if field_lower == 'name':
                return iface.name
            elif field_lower == 'mac' or field_lower == 'mac_address':
                return iface.mac_address
            elif field_lower == 'status':
                return iface.status
            elif field_lower == 'ip' or field_lower == 'ip_address':
                return iface.ip_address or ""
            elif field_lower == 'vendor':
                return iface.vendor or ""
            elif field_lower == 'driver':
                return iface.driver or ""
            elif field_lower == 'type':
                return iface.interface_type or ""
            else:
                return ""

        return sorted(interfaces, key=get_sort_key, reverse=reverse)

    @staticmethod
    def to_table(
        interfaces: List[NetworkInterface],
        fields: Optional[List[str]] = None
    ) -> str:
        """
        Format interfaces as a table.

        Args:
            interfaces: List of network interfaces
            fields: Fields to include in table

        Returns:
            Formatted table string
        """
        if not interfaces:
            return "No interfaces found."

        if fields is None:
            fields = ['name', 'mac_address', 'status', 'ip_address', 'vendor']

        # Build table header
        col_widths = {field: len(field) for field in fields}

        for iface in interfaces:
            for field in fields:
                value = str(getattr(iface, field, ""))
                col_widths[field] = max(col_widths[field], len(value))

        # Build header row
        header_parts = []
        for field in fields:
            width = col_widths[field]
            header_parts.append(field.upper().ljust(width))

        table = [" | ".join(header_parts)]
        table.append("-" * (sum(col_widths.values()) + (len(fields) - 1) * 3))

        # Build data rows
        for iface in interfaces:
            row_parts = []
            for field in fields:
                value = str(getattr(iface, field, ""))
                width = col_widths[field]
                row_parts.append(value.ljust(width))
            table.append(" | ".join(row_parts))

        return "\n".join(table)


def test_interface_filter():
    """Test the interface filter."""
    print("=" * 60)
    print("Interface Filter Tests")
    print("=" * 60)

    # Create test interfaces
    interfaces = [
        NetworkInterface(
            name="eth0",
            mac_address="00:11:22:33:44:55",
            status="up",
            ip_address="192.168.1.10",
            vendor="Intel",
            driver="e1000"
        ),
        NetworkInterface(
            name="eth1",
            mac_address="00:11:22:33:44:66",
            status="down",
            ip_address=None,
            vendor="Realtek",
            driver="r8169"
        ),
        NetworkInterface(
            name="wlan0",
            mac_address="00:11:22:33:44:77",
            status="up",
            ip_address="192.168.1.20",
            vendor="Atheros",
            driver="ath9k"
        ),
    ]

    print("\nAll interfaces:")
    print(InterfaceFilter.to_table(interfaces))

    print("\n\nActive interfaces only:")
    active = InterfaceFilter.filter_active(interfaces)
    print(InterfaceFilter.to_table(active))

    print("\n\nInterfaces with IP:")
    with_ip = InterfaceFilter.filter_has_ip(interfaces)
    print(InterfaceFilter.to_table(with_ip))

    print("\n\nSearch for 'realtek':")
    search_results = InterfaceFilter.search(interfaces, "realtek")
    print(InterfaceFilter.to_table(search_results))

    print("\n\nSorted by name:")
    sorted_interfaces = InterfaceFilter.sort_by_field(interfaces, 'name')
    print(InterfaceFilter.to_table(sorted_interfaces))


if __name__ == "__main__":
    test_interface_filter()
