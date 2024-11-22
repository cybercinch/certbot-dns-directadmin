#!/bin/bash

# Update version for the release
sed -ie "s/^version = \".*\"/version = \"${1}\"/" pyproject.toml

# Ensure no complaints about drift.
poetry lock --no-update

# Build the package
poetry build
## Configure credentials
#poetry config pypi-token.pypi "${PYPI_TOKEN}"
## Publish package up to PyPi
#poetry publish