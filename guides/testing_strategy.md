# Testing Strategy

We strive for high test coverage, and to add tests for new functionality and
bug fixes that are merged with the code changes.

## Running the tests

Tests require a database, which is trivial with ``docker-compose``.
All tests can be run from the command:

> make test

This starts the database container, enters the web container, runs the unit
tests, behave tests, and calculates the combined code coverage. See
``scripts/test.sh`` for details.

During development, you may want to run a subset of tests. You can enter the
web container with ``make test-shell``, and then run the test commands directly.
See the sections below for details.

## Behave for Behaviour-Driven Development

We are using [Behave][behave] for [behaviour-driven test development][bdd]
(BDD).

- The tests live in: tests/behave/*.feature
- The implementation for the tests live in: tests/behave/steps/*.py
- The data resources the tests use live in: tests/resources/*
- Where * is commonly the same feature to be tested and implemented

[behave]: <https://behave.readthedocs.io/en/latest/> "Behave documentation"
[bdd]: <https://en.wikipedia.org/wiki/Behavior-driven_development> "Behavior-driven development on WikiPedia"

### To write a new test:

* Create a feature file for your test in tests/behave/
    - This file should describe your feature with different scenarios.
    - These feature files are written using the Gherkin language.
        - Gherkin is intended as a common language to bridge engineers and non-engineers.
        - It's used to understand the current working operations and expectations around software
        - Steps are the different events that happen in a sequence within a Scenario for a Feature.
            - Given (some contextual set up)
            - When (this event occurs)
            - Then (this is the expected reaction and response)
* Create implementation for your steps in tests/behave/steps/
    - These steps are the glue code that maps the Gherkin files to operate and test the expected results and operations
    - This object should contain the mappings to the features you've created in the previous step.
    - Using Behave with the Gherkin files allows for the mapping to the behave decorators
        - Given (@given, @step)
        - When (@when, @step)
        - Then (@then, @step)
    - Following BDD and TDD, the red-green refactor pattern is expected.
        - At this point you should now be able to run your tests.
        - Since nothing is yet implemented all your new tests should fail.
        - As you implement your tests should begin to pass.

### To run the tests:
You can run the suite by first entering the web container:
> make test-shell

And then running the installed ``behave`` with the folder path:
> behave tests/behave/

To stop on the first failure:
> behave tests/behave/ --stop

## Pytest for unit tests

We are using [pytest][pytest] for unit testing, as well as integration testing
with the database.

- The tests live in: tests/unit/*.py
- The shared test fixtures live in: tests/unit/conftest.py

[pytest]: <https://docs.pytest.org/en/stable/> "pytest documentation"

### To run the tests:
You can run the suite by first entering the web container:
> make test-shell

And then running the installed ``pytest`` through ``python``, which adds the
current ``app`` folder to the system path first:
> python -m pytest

To stop on the first failure and drop into [pdb][pdb]:
> python -m pytest -sx --pdb

[pdb]: <https://docs.python.org/3/library/pdb.html> "pdb - The Python Debugger"
