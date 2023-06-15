#!/bin/bash

set -euo pipefail

POETRY_RUN="poetry run"

CURRENT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASE_DIR="$(dirname "$CURRENT_DIR")"
DOCKER_COMPOSE=${DOCKER_COMPOSE-"docker-compose"}

# without this, some tests fail because of off-by-timezone errors.
export TZ=UTC

# Create newsletters in basket
cat tests/integration/basket-db-init.sql | $DOCKER_COMPOSE exec -T mysql mariadb -u root -h mysql basket

# Create token in CTMS (will only work with specific CTMS_SECRET, see .sql source)
cat tests/integration/ctms-db-init.sql | $DOCKER_COMPOSE exec -T postgres psql --user postgres -d postgres

# docker-compose run basket django-admin loaddata ./basket/news/fixtures/newsletters.json
$POETRY_RUN pytest tests/integration/
