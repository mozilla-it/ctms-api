# Testing Strategy

We strive for high test coverage, and to add tests for new functionality and
bug fixes that are merged with the code changes.

## Running the tests

Tests require a database, which is trivial with ``docker-compose``.
All tests can be run from the command:

> make test

This starts the database container, enters the web container, runs the unit
tests, and calculates the combined code coverage. See
``scripts/test.sh`` for details.

During development, you may want to run a subset of tests. You can enter the
web container with ``make test-shell``, and then run the test commands directly.
See the sections below for details.

## Pytest for unit tests

We are using [pytest][pytest] for unit testing, as well as integration testing
with the database.

- The tests live in: tests/unit/*.py
- The shared test fixtures live in: tests/unit/conftest.py

[pytest]: <https://docs.pytest.org/en/stable/> "pytest documentation"

### To run the tests:
You can run the suite by first entering the web container:
> make test-shell

And then run the installed ``pytest``:
> pytest

To stop on the first failure and drop into [pdb][pdb]:
> pytest -sx --pdb

[pdb]: <https://docs.python.org/3/library/pdb.html> "pdb - The Python Debugger"

---
[View All Docs](./)
