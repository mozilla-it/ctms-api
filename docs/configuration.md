# Configuration

Most configuration is done through environment variables. In the development
environment, these are stored in files for ease of editing and loading. In
production, they are set as part of the runtime environment.

## Environment Configuration

* ``CTMS_DB_URL`` - The database connection parameters, formatted as a URL.
  In the development environment, this defaults to talk to the ``postgres``
  container. In production, it is set to talk to the provisioned database.
* ``CTMS_DB_POOL_SIZE`` - The database connection parameter ``pool_size`` (default: 10).
  [...view more on sqlalchemy.](https://docs.sqlalchemy.org/en/14/core/engines.html#sqlalchemy.create_engine.params.pool_size)
* ``CTMS_DB_MAX_OVERFLOW`` - The database connection parameter ``max_overflow`` (default: 20).
  [...view more on sqlalchemy.](https://docs.sqlalchemy.org/en/14/core/engines.html#sqlalchemy.create_engine.params.max_overflow)
* ``CTMS_DB_POOL_TIMEOUT_IN_SECONDS`` - The database connection parameter ``pool_timeout``(default: 45s).
  [...view more on sqlalchemy.](https://docs.sqlalchemy.org/en/14/core/engines.html#sqlalchemy.create_engine.params.pool_timeout)
* ``CTMS_SECRET_KEY`` - An encryption key, used for OAuth2 and other hashes.
  Set to a long but non-secret value for development, and set to a randomized
  string for each production deployment.
* ``CTMS_TOKEN_EXPIRATION`` - How long an OAuth2 access token is valid, in seconds.
  If unset, defaults to one hour.
* ``CTMS_SERVER_PREFIX`` - The protocol and domain part of the server name, used
  to construct full URLS. Set to ``http://localhost:8000`` in development, and
  the user-facing prefix in production.
* ``CTMS_USE_MOZLOG`` - Use the JSON
  [MozLog](https://wiki.mozilla.org/Firefox/Services/Logging) format for logs.
  Defaults to `True` as used in production, and is set to `False` for development.
  See the [deployment guide](./deployment_guide.md) for more information on the
  MozLog format.
* ``CTMS_LOGGING_LEVEL`` - The minimum level for logs. Defaults to ``INFO`` if
  unset. Unset in production, and set to ``INFO`` in development.
* ``CTMS_LOG_SQLALCHEMY`` - Determines whether SQLAlchemy logs should be
  emmited. Defaults to ``False`` if unset. Unset in production, and set to
  ``False`` in development.
* ``CTMS_SENTRY_DEBUG`` - If set to True, then sentry initialization and capture is
  logged as well. This may be useful for development, but is not recommended for
  production.
* ``CTMS_FASTAPI_ENV`` - To determine which environment is being run; defaults to `None`.
* ``CTMS_PUBSUB_AUDIENCE`` - Audience (or Server) shared between FxA and CTMS; part of claims analysis to ensure request payload is trustworthy.
* ``CTMS_PUBSUB_EMAIL`` - Email (or Service Account) shared between FxA and CTMS; part of claims analysis to ensure request payload is trustworthy.
* ``CTMS_PUBSUB_CLIENT`` - Client (or Token) shared between FxA and CTMS; part of claims analysis to ensure request payload is trustworthy.

* ``CTMS_UID`` - The user ID of the ``app`` account, used to run the CTMS
  application. If unset, defaults to 10001. On Linux development systems, set
  along with ``CTMS_GID`` to match the development user, for consistent permissions.
* ``CTMS_GID`` - The group ID of the ``app`` account, used to run the CTMS
  application. If unset, defaults to 10001. On Linux development systems, set
  along with ``CTMS_UID`` to match the development user, for consistent permissions.
* ``MK_WITH_SERVICE_PORTS`` - If set to ``--service-ports``, passes that option
  to ``docker run`` commands, allowing access to host-based commands.
* ``MK_KEEP_DOCKER_UP`` - If unset, then ``make test`` runs ``docker-compose down``
  after tests run, shutting down the PostgreSQL container.  If set to ``1``,
  ``make test`` keeps containers running.
* ``PORT`` - The port for the web service. Defaults to 8000 if unset.
* ``SENTRY_DSN`` - The Sentry connection string. The sentry-sdk reads this
  in production. It should be unset in development, except for Sentry testing,
  and after informing operations engineers.


### Environment Configuration Files

The file ``ctms/config.py`` defines the environment settings for the CTMS API.

In the production environment, environment variables are set in the deployment
instances and read by the CTMS API application for configuration. When
possible, the default values of environment variables are appropriate for
production.

In the local development environment, the default configuration is in ``.env``.
The file ``.env.example`` is the ``.env`` template for new developer
environments.

``.env`` is loaded in the ``Makefile``, making those configuration items
available in Makefile targets and commands. ``.env`` is also loaded by
``docker-compose`` and passed to Docker. Some adjust the build process by
setting `ARG` variables in the ``Dockerfile``. Others are passed to the runtime
environment. The CTMS API application then loads these from the environment.

Linux users should set ``CTMS_UID`` and ``CTMS_GID`` to match their user account,
so that files created inside the docker container have the same permissions as
their user account.

---
[View All Docs](./)
