#!/bin/sh

set -e

CURRENT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASE_DIR="$(dirname "$CURRENT_DIR")"

#coverage run --rcfile "${BASE_DIR}/pyproject.toml" -m pytest "${BASE_DIR}/tests/unit/" "$*" #TODO: add unit tests if desired
coverage run --rcfile "${BASE_DIR}/pyproject.toml" --branch -m behave -D BEHAVE_DEBUG_ON_ERROR=no "${BASE_DIR}/tests/behave"
coverage report --rcfile "${BASE_DIR}/pyproject.toml" -m --fail-under 80
coverage html --rcfile "${BASE_DIR}/pyproject.toml"
