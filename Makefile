# Include .env and export it so variables are available in the Makefile.
include .env
export

# Set these in the environment to override them. This is helpful for
# development if you have file ownership problems because the user
# in the container doesn't match the user on your host.
CTMS_UID ?= 10001
CTMS_GID ?= 10001

VENV := $(shell echo $${VIRTUAL_ENV-.venv})
DOCKER_COMPOSE := $(shell echo $${DOCKER_COMPOSE-"docker compose"})
INSTALL_STAMP = $(VENV)/.install.stamp

.PHONY: help
help:
	@echo "Usage: make RULE"
	@echo ""
	@echo "CTMS make rules:"
	@echo ""
	@echo "  build             - build docker containers"
	@echo "  db-only           - run PostgreSQL server"
	@echo "  lint              - lint check for code"
	@echo "  format            - run formatter, fix in place"
	@echo "  setup             - (re)create the database"
	@echo "  shell             - open a shell in the web container"
	@echo "  start             - run the API service"
	@echo "  test              - run test suite"
	@echo "  integration-test  - run integration test suite"
	@echo "  update-secrets - scan repository for secrets and update baseline file, if necessary"
	@echo ""
	@echo "  help    - see this text"


.env:
	echo "Copying .env.example to .env"; \
	cp .env.example .env;

install: $(INSTALL_STAMP)
$(INSTALL_STAMP): poetry.lock
	@if [ -z $(shell command -v poetry 2> /dev/null) ]; then echo "Poetry could not be found. See https://python-poetry.org/docs/"; exit 2; fi
	POETRY_VIRTUALENVS_IN_PROJECT=1 poetry install --no-root
	touch $(INSTALL_STAMP)

.PHONY: build
build: .env
	${DOCKER_COMPOSE} version
	${DOCKER_COMPOSE} build --build-arg userid=${CTMS_UID} --build-arg groupid=${CTMS_GID}

.PHONY: lint
lint: $(INSTALL_STAMP)
	bin/lint.sh

.PHONY: format
format: $(INSTALL_STAMP)
	bin/lint.sh format --fix
	bin/lint.sh lint --fix

.PHONY: db-only
db-only: .env
	${DOCKER_COMPOSE} up postgres-admin

.PHONY: setup
setup: .env
	${DOCKER_COMPOSE} stop postgres-admin
	${DOCKER_COMPOSE} up --wait postgres
	${DOCKER_COMPOSE} exec postgres bash -c 'while !</dev/tcp/postgres/5432; do sleep 1; done'
	${DOCKER_COMPOSE} exec postgres dropdb postgres --user postgres
	${DOCKER_COMPOSE} exec postgres createdb postgres --user postgres
	${DOCKER_COMPOSE} run --rm ${MK_WITH_SERVICE_PORTS} web alembic upgrade head

.PHONY: shell
shell: .env
	${DOCKER_COMPOSE} run ${MK_WITH_SERVICE_PORTS} --rm web bash

.PHONY: start
start: .env
	${DOCKER_COMPOSE} up

.PHONY: test
test: .env $(INSTALL_STAMP)
	COVERAGE_REPORT=1 bin/test.sh

.env.tests: .env setup $(INSTALL_STAMP)
	cp tests/integration/basket.env .env.tests
	poetry run ctms/bin/client_credentials.py -e master@local.host integration-test --save-file creds.json
	echo "CTMS_CLIENT_ID=$(jq -r .client_id creds.json)" >> .env.tests
	echo "CTMS_CLIENT_SECRET=$(jq -r .client_secret creds.json)" >> .env.tests
	rm creds.json

.PHONY: integration-test
integration-test: .env.tests
	echo "Starting containers..."
	${DOCKER_COMPOSE} --profile integration-test up --force-recreate --wait basket
	echo "Start test suite..."
	bin/integration-test.sh
	echo "Done."
ifneq (1, ${MK_KEEP_DOCKER_UP})
	# Due to https://github.com/docker/compose/issues/2791 we have to explicitly
	# rm all running containers
	${DOCKER_COMPOSE} --profile integration-test down --remove-orphans
endif

.PHONY: update-secrets
update-secrets:
	bin/update_baseline.sh
