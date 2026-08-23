# Contributing

For complete details on contribution workflows, local setup, and testing steps, please refer to the main [CONTRIBUTING.md](../CONTRIBUTING.md) in the repository root.

## Quick Reference Commands

### Set up local dev environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run tests:
```bash
pytest
```

### Run styling/lint checks:
```bash
ruff check .
ruff format --check .
```
