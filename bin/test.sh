#!/bin/bash

set -euo pipefail

POETRY_RUN="poetry run"

CURRENT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASE_DIR="$(dirname "$CURRENT_DIR")"

# without this, some tests fail because of off-by-timezone errors.
export TZ=UTC

$POETRY_RUN coverage run --rcfile "${BASE_DIR}/pyproject.toml" -m pytest
$POETRY_RUN coverage report --rcfile "${BASE_DIR}/pyproject.toml" -m --fail-under 80
$POETRY_RUN coverage html --rcfile "${BASE_DIR}/pyproject.toml"
