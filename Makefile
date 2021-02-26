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


.PHONY: build
build:
	docker-compose -f ./docker-compose.yaml -f ./tests/docker-compose.test.yaml build

.PHONY: db-only
db-only:
	docker-compose -f ./docker-compose.yaml -f ./tests/docker-compose.test.yaml run --service-ports postgres

.PHONY: setup
setup:
	docker-compose up -d postgres
	docker-compose exec postgres bash -c 'while !</dev/tcp/postgres/5432; do sleep 1; done'
	docker-compose exec postgres dropdb postgres --user postgres
	docker-compose exec postgres createdb postgres --user postgres
	docker-compose run --rm web python -m alembic upgrade head

.PHONY: shell
shell:
	docker-compose -f ./docker-compose.yaml run --rm web bash

.PHONY: start
start:
	docker-compose up

.PHONY: test
test:
	docker-compose -f ./docker-compose.yaml -f ./tests/docker-compose.test.yaml run tests

.PHONY: test-shell
test-shell:
	docker-compose -f ./docker-compose.yaml -f ./tests/docker-compose.test.yaml run --rm web bash
