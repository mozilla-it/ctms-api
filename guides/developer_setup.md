## Developer Setup
Technologies and tools in use:
- Poetry: https://python-poetry.org/
- Pre-commit: https://pre-commit.com/
- Docker: https://www.docker.com/
- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://pydantic-docs.helpmanual.io/
- SQLAlchemy: https://www.sqlalchemy.org/
- Alembic: https://alembic.sqlalchemy.org
- ...

---
## Poetry

## Installation
Install Poetry for osx/linux:

```sh
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
```

## Install Dependencies
Install prod dependencies in pyproject.toml through poetry:

```sh
poetry install --no-dev
```

Install ALL deps including DEV dependencies:
```sh
poetry install
```

### In Use
Opens shell with corresponding dependencies to the poetry(.lock) in the directory that you make the call:

```sh
poetry shell
```

Runs command with poetry venv:

```sh
poetry run {command}
```

### Adding Dependencies
Add new dependencies in pyproject.toml through poetry:

```sh
poetry add {pypi-package}
```

### Exiting Poetry Shell

Run the following command to exit `poetry shell` while in a shell.

```sh
exit
```

The command `deactivate` will not work to full disengage the poetry shell as it does with `venv`.

[...view poetry site for further documentation and details.](https://python-poetry.org/)

---
## Pre-commit

### Install the Hooks
Using poetry (pre-commit is located in the [pyproject.toml](../pyproject.toml) )

```sh
poetry shell
pre-commit install
```

You should get the following response after installing pre-commit into the githooks:

```
pre-commit installed at .git/hooks/pre-commit
```

Reinstall the pre-commit hooks when there are changes to the `.pre-commit-config.yaml` file.

### Run on the Entire Codebase

Run the following command where you installed pre-commit.
```sh
pre-commit run --all-files
```

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
```sh
docker build --tag ctms-api --file docker/Dockerfile .
```

Stop the build at optional stages (development, lint, test, production) with the --target option:
```sh
docker build --tag ctms-api --file docker/Dockerfile . --target <stage>
```

#### Optional
It is also possible to build the full image through the provided scripts:
```sh
poetry run scripts/build.sh
```

---
## Using Docker Compose and the Makefile
`docker-compose` is a tool for configuring and running Docker containers, and is
useful for running PostgreSQL and CTMS together in a development environment.

### Installation
`docker-compose` is included with Docker Desktop for Mac and Windows. For other systems,
see [Install Docker Compose](https://docs.docker.com/compose/install/).

`make` is included on some operating systems and an optional install on others. For
example, `make` is part of the Windows Subsystem for Linux on Windows 10 (see the
[Installation Guide](https://docs.microsoft.com/en-us/windows/wsl/install-win10) for
installing).

To test that they are working:

```sh
make help  # Shows the CTMS make rules
make build # Build the docker containers
```

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
## SQLAlchemy and Alembic

### Details
The usage of these tools is complex and extends beyond this document. The
best place to read to understand how to create/apply migrations and such things
is [the Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html#create-a-migration-script).

To create or recreate a database with empty tables:

```sh
make setup
```

To create a new migration file based on updated SQLAlchemy models:

```sh
make shell  # To enter the web container
alembic revision -m "A short description of the change"
exit
```

Edit the generated migration script, confirm it does what you meant,
and adjust or delete and recreate as needed.

The revision may be detected as secrets at compile time. You can mark
them as allowed:

```python
revision = "3f8a97b79852"  # pragma: allowlist secret
```

To run this and other migrations on an existing database:

```sh
make shell  # Enter the web container
alembic upgrade head
exit
```

---
## OAuth2 Client Credentials

The API uses [OAuth 2 Client Credentials](https://oauth.net/2/grant-types/client-credentials/)
for authentication. To generate credentials for your development environment:

```sh
make shell  # Enter the web container
ctms/bin/client_credentials.py test --email test@example.com
```

This will print out new client credentials, such as:

```
Your OAuth2 client credentials are:

      client_id: id_test
  client_secret: secret_dGhpcyBpcyBubyBzZWNyZXQu

...
```

You can use these on the interactive Swagger docs by clicking the "**Authorize**" button.

---
## Next Steps

### Git Strategy
Please view the [Git Strategy](git_strategy.md)

### Testing
Please view the [Testing Strategy](testing_strategy.md)

---
[View All Docs](./)
