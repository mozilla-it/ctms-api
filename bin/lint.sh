#!/bin/bash

set -euo pipefail

POETRY_RUN="poetry run"

CURRENT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASE_DIR="$(dirname "$CURRENT_DIR")"
HAS_GIT="$(command -v git || echo '')"
echo $HAS_GIT

$POETRY_RUN bandit -lll --recursive "${BASE_DIR}" --exclude "${BASE_DIR}/poetry.lock,${BASE_DIR}/.venv,${BASE_DIR}/.mypy,${BASE_DIR}/build"

if [ -n "$HAS_GIT" ]; then
    # Scan only files checked into the repo, omit poetry.lock
    SECRETS_TO_SCAN=`git ls-tree --full-tree -r --name-only HEAD | grep -v poetry.lock`
    $POETRY_RUN detect-secrets-hook $SECRETS_TO_SCAN --baseline .secrets.baseline
fi

$POETRY_RUN isort --check-only "${BASE_DIR}"
$POETRY_RUN black --check "${BASE_DIR}"
$POETRY_RUN mypy "${BASE_DIR}/ctms"
$POETRY_RUN pylint "${BASE_DIR}/ctms" "${BASE_DIR}/tests/unit"
