#!/bin/bash

set -euo pipefail

DOCKER_COMPOSE=${DOCKER_COMPOSE:-"docker-compose"}
POETRY_RUN="poetry run"

CURRENT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASE_DIR="$(dirname "$CURRENT_DIR")"

# without this, some tests fail because of off-by-timezone errors.
export TZ=UTC

${DOCKER_COMPOSE} up --wait postgres

$POETRY_RUN coverage run --rcfile "${BASE_DIR}/pyproject.toml" -m pytest $@

if [[ -z "${COVERAGE_REPORT-x}" ]]; then
    $POETRY_RUN coverage report --rcfile "${BASE_DIR}/pyproject.toml" -m --fail-under 80
    $POETRY_RUN coverage html --rcfile "${BASE_DIR}/pyproject.toml"
fi


if [[ -z "${MK_KEEP_DOCKER_UP-x}" ]]; then
    # Due to https://github.com/docker/compose/issues/2791 we have to explicitly
    # rm all running containers
    ${DOCKER_COMPOSE} down
fi
