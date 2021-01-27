## Developer Setup
Technologies and tools in use:
- Poetry: https://python-poetry.org/
- Pre-commit: https://pre-commit.com/
- Docker: https://www.docker.com/
- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://pydantic-docs.helpmanual.io/
- ...

---
## Poetry

## Installation
Install Poetry for osx/linux:
> curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python

## Install Dependencies
Install prod dependencies in pyproject.toml through poetry:
> poetry install --no-dev

Install ALL deps including DEV dependencies:
> poetry install

### In Use
Opens shell with corresponding dependencies to the poetry(.lock) in the directory that you make the call:
> poetry shell

> `Provides access to all the dependencies installed`

Runs command with poetry venv:
> poetry run {command}

### Adding Dependencies
Add new dependencies in pyproject.toml through poetry:
> poetry add {pypi-package}

### Exiting Poetry Shell

Run the following command to exit `poetry shell` while in a shell.
> exit

The command `deactivate` will not work to full disengage the poetry shell as it does with `venv`.

[...view poetry site for further documentation and details.](https://python-poetry.org/)

---
## Pre-commit

### Install the Hooks
Using poetry (pre-commit is located in the [pyproject.toml](../pyproject.toml) )

> poetry shell
> pre-commit install

You should get the following response after installing pre-commit into the githooks:

> pre-commit installed at .git/hooks/pre-commit

Reinstall the pre-commit hooks when there are changes to the `.pre-commit-config.yaml` file.

### Run on the Entire Codebase

Run the following command where you installed pre-commit.
> pre-commit run --all-files

### Passively Runs on Git "Commit"
When you commit in git, the pre-commit hooks will engage and perform the outlined steps.

#### Bypass Hook (Not Recommended)
The option `--no-verify` should allow a committer to bypass the hooks.

---
## Docker

### Installation
Install Docker here: https://docs.docker.com/get-docker/

### Building
Build images with:
> docker build --tag ctms-api --file docker/Dockerfile .

Stop the build at optional stages (development, lint, test, production) with the --target option:
> docker build --name ctms-api --file docker/Dockerfile . --target <stage>

#### Optional
It is also possible to build the full image through the provided scripts:
> poetry run scripts/build.sh

---
## FastAPI

### Details
Web-Framework for building APIs with Python that provides short, easy, and
intuitive decorator-based annotations for routing (similar to Flask), but
also provides OpenAPI and JSON Schema portals for API viewing.

---
## Pydantic

### Details
Data Modeling and validation package that enforces type hints at
runtime and provides friendly errors for easy debugging.

---
## Next Steps

### Git Strategy
Please view the [Git Strategy](git_strategy.md)

### Testing
Please view the [Testing Strategy](testing_strategy.md)

---
[View All Docs](./)
