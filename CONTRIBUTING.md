# Contributing to MCPToolForge

Thank you for your interest in contributing to MCPToolForge! We welcome all contributions, including bug fixes, feature requests, and documentation improvements.

---

## Getting Started

### 1. Fork and Clone
Fork the repository on GitHub, and clone your fork locally:
```bash
git clone https://github.com/<your-username>/toolforge.git
cd toolforge
```

### 2. Set Up Virtual Environment
Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Development Dependencies
Install the package in editable mode with development dependencies:
```bash
pip install -e ".[dev]"
```

---

## Contribution Workflow

### 1. Create a Branch
Always create a new branch for your work:
```bash
git checkout -b my-feature-branch
```

### 2. Make Changes & Write Tests
Implement your changes. If you are adding a feature or fixing a bug, please write corresponding tests in the `tests/` directory to verify the behavior.

### 3. Run the Test Suite
Ensure all tests pass successfully before committing:
```bash
pytest
```

### 4. Run Lint & Format Checks
We use Ruff to maintain code quality and formatting. Run these checks to verify style compliance:
```bash
# Lint checks
ruff check .

# Formatting checks
ruff format --check .
```

### 5. Commit Changes
We use **Conventional Commits** for automated release creation and changelog updates. Ensure your commit messages follow this format:
- `feat: add resource template capability` (for new features)
- `fix: correct validation type coercion logic` (for bug fixes)
- `docs: update quick-start guide in README` (for documentation changes)
- `chore: update dependencies` (for maintenance tasks)

### 6. Submit a Pull Request
Push your branch to GitHub and open a Pull Request (PR) against the `main` branch of the official repository.

---

## Important Rules
- **No Secrets**: Never commit API keys, credentials, or private configuration files.
- **Keep PRs Focused**: Each Pull Request should address a single concern.
- **Update Documentation**: If your PR modifies a public API, make sure the README or `docs/` files are updated accordingly.
