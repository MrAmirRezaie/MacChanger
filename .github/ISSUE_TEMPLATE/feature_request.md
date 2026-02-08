/* GitHub Feature Request Template */
name: Feature Request
description: Suggest an idea for MAC Address Spoofer
title: "[FEATURE] "
labels: ["enhancement"]
assignees: ["MrAmirRezaie"]

body:
  - type: markdown
    attributes:
      value: |
        Thanks for the feature request! Please describe the feature below.

  - type: textarea
    id: feature_description
    attributes:
      label: Feature Description
      description: What would you like to see added?
      placeholder: |
        I would like MAC Address Spoofer to...
    validations:
      required: true

  - type: textarea
    id: use_case
    attributes:
      label: Use Case
      description: Why is this feature needed?
      placeholder: |
        This would help because...
    validations:
      required: true

  - type: textarea
    id: proposed_solution
    attributes:
      label: Proposed Solution
      description: How do you think it should work?
      placeholder: |
        The tool could...
    validations:
      required: false

  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives Considered
      description: What other approaches could work?
      placeholder: |
        Other options:
        1. ...
        2. ...
    validations:
      required: false

  - type: checkboxes
    id: checklist
    attributes:
      label: Checklist
      options:
        - label: I have checked existing issues/features
          required: true
        - label: This is not a duplicate request
          required: true

  - type: checkboxes
    id: terms
    attributes:
      label: Agreement
      options:
        - label: I understand this is for authorized testing only
          required: true
