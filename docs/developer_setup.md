## Developer Setup

Prerequisites

- Make: https://www.gnu.org/software/make/
- Poetry: https://python-poetry.org/
- Docker: https://www.docker.com/
- Pre-commit: https://pre-commit.com/
- [psycopg2 build prerequisites](https://www.psycopg.org/docs/install.html#build-prerequisites)

## Setup Dependencies

To set up dependencies necessary for local development, run:

```sh
make install
```

---
## Pre-commit

### Install the Hooks

```sh
poetry run pre-commit install
```

You should get the following response after installing pre-commit into the githooks:

```
pre-commit installed at .git/hooks/pre-commit
```

Reinstall the pre-commit hooks when there are changes to the `.pre-commit-config.yaml` file.

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

### Linux Users
Linux users will want to set the user ID and group ID used in the container.
Users of Docker Desktop for Mac or Windows can skip this step.

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
## Database

To create or recreate a database with empty tables:

```sh
make setup
```

### Migrations

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
## Python
CTMS is a Python application. We tend to keep the application up to date with
the latest version of Python -- we pin to the patch version throughout the
repository.

Dependabot will submit pull requests to update the Python version in the
Dockerfile, but will miss other places like `pyproject.toml` and Github Action
workflow files. This `sed`[^1] snippet will find/replace all Python versions in
one go - in this example, from version `A.B.C` to `X.Y.Z`:
```bash
git ls-files | xargs sed -i 's/A\.B\.C/X\.Y\.Z/g'
```

Manually inspect the changes to filter out false positives.

### Keeping Poetry up to date
Poetry is pinned to a specific version in a few places throughout the
repository. This `sed`[^1] snippet will find/replace all of these insances in
one go - in this example, from version `A.B.C` to `X.Y.Z`:
```bash
git ls-files | xargs sed -i 's/A\.B\.C/X\.Y\.Z/g'
```

Manually inspect the changes to filter out false positives.

---
[View All Docs](./)

[^1]: Use [`gnu-sed`](https://formulae.brew.sh/formula/gnu-sed#default) on Mac for command compatability
