# Include .env and export it so variables are available in the Makefile.
include .env
export

# Set these in the environment to override them. This is helpful for
# development if you have file ownership problems because the user
# in the container doesn't match the user on your host.
CTMS_UID ?= 10001
CTMS_GID ?= 10001

VENV := $(shell echo $${VIRTUAL_ENV-.venv})
INSTALL_STAMP = $(VENV)/.install.stamp

.PHONY: help
help:
	@echo "Usage: make RULE"
	@echo ""
	@echo "CTMS make rules:"
	@echo ""
	@echo "  build   - build docker containers"
	@echo "  lint    - lint check for code"
	@echo "  setup   - (re)create the database"
	@echo "  start   - run the API service"
	@echo ""
	@echo "  test        - run test suite"
	@echo "  shell       - open a shell in the web container"
	@echo "  db-only     - run PostgreSQL server"
	@echo ""
	@echo "  help    - see this text"


.env:
	@if [ ! -f .env ]; \
	then \
	echo "Copying env.dist to .env..."; \
	cp docker/config/env.dist .env; \
	fi

install: $(INSTALL_STAMP)
$(INSTALL_STAMP): poetry.lock
	@if [ -z $(shell command -v poetry 2> /dev/null) ]; then echo "Poetry could not be found. See https://python-poetry.org/docs/"; exit 2; fi
	POETRY_VIRTUALENVS_IN_PROJECT=1 poetry install --no-root
	touch $(INSTALL_STAMP)

.PHONY: build
build: .env
	docker-compose build --build-arg userid=${CTMS_UID} --build-arg groupid=${CTMS_GID}

.PHONY: lint
lint: .env $(INSTALL_STAMP)
	bin/lint.sh

.PHONY: db-only
db-only: .env
	docker-compose up postgres-admin

.PHONY: setup
setup: .env
	docker-compose stop postgres-admin
	docker-compose up -d postgres
	docker-compose exec postgres bash -c 'while !</dev/tcp/postgres/5432; do sleep 1; done'
	docker-compose exec postgres dropdb postgres --user postgres
	docker-compose exec postgres createdb postgres --user postgres
	docker-compose run --rm ${MK_WITH_SERVICE_PORTS} web alembic upgrade head

.PHONY: shell
shell: .env
	docker-compose run ${MK_WITH_SERVICE_PORTS} --rm web bash

.PHONY: start
start: .env
	docker-compose up

.PHONY: test
test: .env
	docker-compose run --rm ${MK_WITH_SERVICE_PORTS} tests
ifneq (1, ${MK_KEEP_DOCKER_UP})
	# Due to https://github.com/docker/compose/issues/2791 we have to explicitly
	# rm all running containers
	docker-compose down
endif

