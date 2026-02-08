# Contributors Guide

Thank you for your interest in contributing to MAC Address Spoofer!

## Code of Conduct

All contributors must:
- Use the tool only for authorized, legal purposes
- Follow the strict license terms in LICENSE file
- Respect intellectual property and security
- Maintain ethical standards

Violations will result in immediate contributor revocation.

## Contribution Guidelines

### Before You Start

1. **Read the LICENSE** - Understand the strict terms
2. **Check existing issues** - Avoid duplicate work
3. **Review the code** - Understand the architecture
4. **Run tests** - Ensure baseline passes: `python tests.py`

### Making Changes

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Make your changes** with clear commit messages
4. **Add tests** for new functionality
5. **Run full test suite**: `python tests.py`
6. **Update documentation** if needed
7. **Submit a pull request**

### Code Style

- Follow PEP 8 conventions
- Use meaningful variable names
- Include docstrings for functions and classes
- Add type hints where applicable
- Keep functions focused and concise

### Testing Requirements

All contributions must:
- Pass all existing tests
- Include tests for new code
- Achieve > 80% code coverage for new modules
- Include error scenario tests

Run tests:
```bash
python tests.py
```

### Documentation

Update documentation for:
- New commands or options
- Changed behavior
- New modules or functions
- Configuration changes

## Areas for Contribution

### High Priority
- [ ] Additional vendor OUI patterns
- [ ] Support for more network drivers
- [ ] Windows driver-level MAC spoofing
- [ ] GUI interface

### Medium Priority
- [ ] Persistent spoofing profiles
- [ ] Network statistics integration
- [ ] Scheduled spoofing tasks
- [ ] Cloud integration

### Low Priority
- [ ] Additional language translations
- [ ] Third-party tool integrations
- [ ] Extended documentation examples

## Pull Request Process

1. Update README.md with any new features
2. Update tests to cover new functionality
3. Ensure all tests pass
4. Request review from maintainers
5. Address feedback and review comments
6. Maintainer approval required

## Reporting Issues

### Security Issues

Do NOT create a public issue for security vulnerabilities. Email details privately.

### Bug Reports

Include:
- Operating system and version
- Python version (`python --version`)
- Exact commands that failed
- Error messages (full traceback)
- Steps to reproduce

### Feature Requests

Include:
- Clear description of the feature
- Use cases and examples
- Why existing features don't meet the need
- Proposed implementation (optional)

## License Compliance

By contributing, you agree that:
- Your contributions are your own original work
- You have the right to contribute
- Your work will be licensed under the same terms
- You understand the strict license restrictions

## Questions?

Review:
- [README.md](./README.md) - General usage
- [QUICKSTART.md](./QUICKSTART.md) - Quick examples
- [LICENSE](./LICENSE) - Legal terms

---

**Thank you for making MAC Address Spoofer better!**
