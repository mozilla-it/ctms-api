# Include .env and export it so variables are available in the Makefile.
include .env
export


.PHONY: help
help:
	@echo "Usage: make RULE"
	@echo ""
	@echo "CTMS make rules:"
	@echo ""
	@echo "  build   - build docker containers"
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
	docker-compose -f ./docker-compose.yaml -f ./tests/docker-compose.test.yaml build

.PHONY: db-only
db-only: .env
	docker-compose -f ./docker-compose.yaml -f ./tests/docker-compose.test.yaml run --service-ports postgres

.PHONY: setup
setup: .env
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
	docker-compose -f ./docker-compose.yaml -f ./tests/docker-compose.test.yaml run --rm ${MK_WITH_SERVICE_PORTS} tests
ifneq (1, ${MK_KEEP_DOCKER_UP})
	# Due to https://github.com/docker/compose/issues/2791 we have to explicitly
	# rm all running containers
	docker-compose down
endif

.PHONY: test-shell
test-shell: .env
	docker-compose -f ./docker-compose.yaml -f ./tests/docker-compose.test.yaml run --rm ${MK_WITH_SERVICE_PORTS} web bash
