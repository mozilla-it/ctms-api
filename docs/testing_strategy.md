# Testing Strategy

We strive for high test coverage and to add tests for new functionality and
bug fixes that are merged with the code changes.

## Running the tests

All tests can be run with the command:

> make test

This starts a database container, waits for it to be ready, runs the unit
tests, and calculates the combined code coverage. See ``bin/test.sh`` for
details.

## Pytest for unit tests

We are using [pytest][pytest] for unit testing as well as integration testing
with the database.

- The tests live in: `tests/unit/*.py`
- The shared test fixtures live in: `tests/unit/conftest.py`

### Running tests manually:
Make sure you have dependencies installed and a postgres database running with
all of the migrations run

And then run the installed ``pytest``:
```sh
pytest
```

To stop on the first failure and drop into [pdb][pdb]:
```sh
pytest -sx --pdb
```

To run a test or tests whose name matchs a substring:
```sh
pytest -k "substring"
```

View the [pytest] documentation for more options.

[pdb]: <https://docs.python.org/3/library/pdb.html> "pdb - The Python Debugger"
[pytest]: <https://docs.pytest.org/en/stable/> "pytest documentation"

---
[View All Docs](./)
