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
Install Poetry for osx/linux (please confirm via the [poetry docs](https://python-poetry.org/docs/#installation)):

```sh
curl -sSL https://install.python-poetry.org | python3 -
```

## Setup Dependencies
To set up dependencies necessary for local development, run:

```sh
make install
```

If these fail with an error like:

```
Error: pg_config executable not found.

pg_config is required to build psycopg2 from source.  Please add the directory
containing pg_config to the $PATH or specify the full executable path with the
option:
...
```

then you need to install the `psycopg2` prerequisites, like the PostgreSQL development package. See
[psycopg2 build prerequisites](https://www.psycopg.org/docs/install.html#build-prerequisites)
for help.

### Using Poetry
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

### Updating Dependencies
To update a dependency to the latest version:

```sh
poetry add {pypi-package}@latest
```

This can also be used to update via constraint:

```sh
poetry add {pypi-package}@^2.1.0
poetry add {pypi-package}>=2.0.0,<3.0.0
```

Using ``poetry add`` will also update ``pyproject.toml``, which is easier for a
human to parse than ``poetry.lock``.

To update all dependencies in ``poetry.lock``, but not ``pyproject.toml``:

```sh
poetry update
```

To update a single dependency in ``poetry.lock``:

```sh
poetry update {pypi-package}
```

### Exiting Poetry Shell

Run the following command to exit `poetry shell` while in a shell.

```sh
exit
```

The command `deactivate` might not work to full disengage the poetry shell as it does with `venv`.

[...view poetry site for further documentation and details.](https://python-poetry.org/)

---
## Pre-commit

### Install the Hooks
Using poetry (pre-commit is located in the [pyproject.toml](../pyproject.toml) )

```sh
poetry run pre-commit install
```

You should get the following response after installing pre-commit into the githooks:

```
pre-commit installed at .git/hooks/pre-commit
```

Reinstall the pre-commit hooks when there are changes to the `.pre-commit-config.yaml` file.

### It Passively Runs on Git "Commit"
When you commit in git, the pre-commit hooks will engage and perform the outlined steps.

### Force Run on the Entire Codebase (Optional)

Run the following to check all files
```sh
poetry run pre-commit run --all-files
```

### Bypass Hook (Not Recommended)
The option `--no-verify` allows a committer to bypass the hooks when committing:

```sh
git commit --no-verify
```

---
## Docker

### Installation
Install Docker here: https://docs.docker.com/get-docker/

### Linux Users
Linux users will want to set the user ID and group ID used in the container.
User of Docker Desktop for Mac or Windows can skip this step.

Create a ``.env`` environment file, if it isn't already created:

```sh
make .env
```

Edit this file, and set these variables:
```sh
CTMS_UID=1000
CTMS_GID=1000
```

Set these to your user ID and group ID. These commands might return them:

```sh
id -u # Your user ID
id -g # Your group ID
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

### Viewing the Database
The tool [adminer](https://www.adminer.org/) is included as `postgres-admin`,
allowing you to view the database in the development environment.  To start it:

```sh
docker-compose up -d postgres-admin
```

The adminer website runs at http://localhost:8080. Log in with these credentials:

* System: PostgreSQL (from dropdown)
* Server: `postgres`
* Username: `postgres`
* Password: `postgres`
* Database: `postgres`

---
## FastAPI

### Details
Web-Framework for building APIs with Python that provides short, easy, and
intuitive decorator-based annotations for routing (similar to Flask), but
also provides OpenAPI and JSON Schema portals for API viewing.
- https://fastapi.tiangolo.com/

---
## Pydantic

### Details
Data Modeling and validation package that enforces type hints at
runtime and provides friendly errors for easy debugging.
- https://pydantic-docs.helpmanual.io/
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
alembic revision --autogenerate -m "A short description of the change"
black /app/migrations/versions/
exit
```

Edit the generated migration script, confirm it does what you meant,
and adjust or delete and recreate as needed.

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
## Configuration
See [Configuration](configuration.md) for local and production configuration settings.

---
## Approaching this repo

After you've done the necessary developer setup, try 'make' for some quick first steps.

> Use `make help` to see additional make commands that help with setup, starting, and testing.

---
[View All Docs](./)
