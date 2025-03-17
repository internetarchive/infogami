#!/usr/bin/env bash
# Used for GitHub Actions
set -e -v

# Run linters and formatters
black --skip-string-normalization .
codespell \
    --exclude-file=infogami/core/files/js/repetition/repetition-model.js
ruff check .  # See pyproject.toml for args
mypy --install-types --non-interactive .
