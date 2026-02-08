/* GitHub Issue Template */
name: Bug Report
description: Report a bug or issue with MAC Address Spoofer
title: "[BUG] "
labels: ["bug"]
assignees: ["MrAmirRezaie"]

body:
  - type: markdown
    attributes:
      value: |
        Thanks for reporting a bug! Please fill out the form below.

  - type: checkboxes
    id: checklist
    attributes:
      label: Pre-submission checklist
      options:
        - label: I have read the README and QUICKSTART
          required: true
        - label: I have checked existing issues
          required: true
        - label: I ran `install_requirements.py` and all checks passed
          required: true
        - label: I ran the test suite and it passed
          required: true

  - type: textarea
    id: description
    attributes:
      label: Bug Description
      description: What is the bug? What did you expect?
      placeholder: |
        The tool does X but I expected it to do Y...
    validations:
      required: true

  - type: textarea
    id: reproduction
    attributes:
      label: Steps to Reproduce
      description: How can we reproduce this bug?
      placeholder: |
        1. Run command...
        2. Observe...
        3. Get error...
    validations:
      required: true

  - type: textarea
    id: error
    attributes:
      label: Error Message
      description: Full error message or traceback
      render: python
      placeholder: "Traceback (most recent call last):\n  ..."
    validations:
      required: false

  - type: dropdown
    id: os
    attributes:
      label: Operating System
      options:
        - Windows 10
        - Windows 11
        - Ubuntu 18.04
        - Ubuntu 20.04
        - Ubuntu 22.04
        - Debian 10
        - Debian 11
        - Fedora 30+
        - macOS 10.14
        - macOS 11
        - macOS 12
        - macOS 13
        - Other
    validations:
      required: true

  - type: input
    id: python_version
    attributes:
      label: Python Version
      description: Output of `python --version`
      placeholder: "Python 3.10.5"
    validations:
      required: true

  - type: textarea
    id: context
    attributes:
      label: Additional Context
      description: Any other relevant information?
      placeholder: "e.g., recently updated Python, using virtualization..."
    validations:
      required: false

  - type: checkboxes
    id: terms
    attributes:
      label: Agreement
      options:
        - label: I understand this is for authorized testing only
          required: true
        - label: I take responsibility for my use of this tool
          required: true
