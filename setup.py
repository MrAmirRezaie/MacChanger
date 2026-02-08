"""
Setup configuration for MAC Address Spoofer package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="mac-address-spoofer",
    version="1.0.0",
    author="MrAmirRezaie",
    author_email="",
    description="Cross-platform MAC address spoofing tool with automatic error detection and rollback",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MrAmirRezaie/MacChanger",
    project_urls={
        "Bug Tracker": "https://github.com/MrAmirRezaie/MacChanger/issues",
        "Documentation": "https://github.com/MrAmirRezaie/MacChanger#readme",
        "Source Code": "https://github.com/MrAmirRezaie/MacChanger",
    },
    license="MIT with Additional Restrictions",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Telecommunications Industry",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Operating System :: Microsoft :: Windows :: Windows 11",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Networking",
        "Topic :: System :: Hardware",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "mac-spoofer=mac_spoofer_cli:main",
        ],
    },
    keywords=[
        "mac",
        "spoof",
        "network",
        "ethernet",
        "adapter",
        "windows",
        "linux",
        "macos",
        "security",
        "testing",
        "system-administration",
    ],
    include_package_data=True,
    zip_safe=False,
)
