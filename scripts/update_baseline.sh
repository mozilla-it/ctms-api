#!/bin/bash

set -e

CURRENT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASE_DIR="$(dirname "$CURRENT_DIR")"

detect-secrets scan . --exclude-files "(poetry.lock$)|(htmlcov/)" > .secrets.baseline
