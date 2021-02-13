.PHONY: test
test:
	docker-compose -f ./docker-compose.yaml -f ./tests/docker-compose.test.yaml run tests

.PHONY: start
start:
	docker-compose up

.PHONY: test-shell
test-shell:
	docker-compose -f ./docker-compose.yaml -f ./tests/docker-compose.test.yaml run --rm web bash
