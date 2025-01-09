#!/bin/bash

set -euo pipefail

POETRY_RUN="poetry run"

CURRENT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASE_DIR="$(dirname "$CURRENT_DIR")"
DOCKER_COMPOSE=${DOCKER_COMPOSE-"docker compose"}

# without this, some tests fail because of off-by-timezone errors.
export TZ=UTC

# Create newsletters in basket
cat tests/integration/basket-db-init.sql | $DOCKER_COMPOSE exec -T mysql mariadb -u root -h mysql basket

# We don't capture tests output to trace retries of failing assertions.
$POETRY_RUN pytest --capture=no tests/integration/
