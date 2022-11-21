# Include .env and export it so variables are available in the Makefile.
include .env
export

# Set these in the environment to override them. This is helpful for
# development if you have file ownership problems because the user
# in the container doesn't match the user on your host.
CTMS_UID ?= 10001
CTMS_GID ?= 10001

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
	@echo "  test-shell  - open a shell in test environment"
	@echo "  db-only     - run PostgreSQL server"
	@echo ""
	@echo "  help    - see this text"


.env:
	@if [ ! -f .env ]; \
	then \
	echo "Copying env.dist to .env..."; \
	cp docker/config/env.dist .env; \
	fi


.PHONY: build
build: .env
	docker-compose -f ./docker-compose.yaml build \
		--build-arg userid=${CTMS_UID} --build-arg groupid=${CTMS_GID}

.PHONY: lint
lint: .env
	docker-compose run --rm --no-deps web bash ./docker/lint.sh

.PHONY: db-only
db-only: .env
	docker-compose -f ./docker-compose.yaml run --service-ports postgres postgres-admin

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
	docker-compose -f ./docker-compose.yaml run ${MK_WITH_SERVICE_PORTS} --rm web bash

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

.PHONY: test-shell
test-shell: .env
	docker-compose -f ./docker-compose.yaml run --rm ${MK_WITH_SERVICE_PORTS} web bash
