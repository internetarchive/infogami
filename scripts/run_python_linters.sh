#!/usr/bin/env bash
# Used for GitHub Actions
set -e -v

# Run linters and formatters
black --skip-string-normalization --check .
codespell  # See setup.cfg for args
ruff .  # See pyproject.toml for args
mypy --install-types --non-interactive .
