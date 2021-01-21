# Testing Strategy

We are using Behave and Jinja2 to templatize data for testing

See Behave https://behave.readthedocs.io/en/latest/

- The tests live in: tests/behave/*.feature
- The implementation for the tests live in: tests/behave/steps/*.py
- The data resources the tests use live in: tests/resources/*
- Where * is commonly the same feature to be tested and implemented

---

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

---

### How to run the tests:
You can run the suite by shelling into poetry:
> poetry shell

And then running the installed behave with the folder path:
> behave tests/behave/

### Using script
You could also opt to use this script to perform the tests locally:
> poetry run scripts/test.sh
