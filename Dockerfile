FROM python:3.12.7 AS python-base

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=off \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PYSETUP_PATH="/opt/pysetup"

RUN python3 -m venv $POETRY_HOME && \
    $POETRY_HOME/bin/pip install poetry && \
    $POETRY_HOME/bin/poetry --version

WORKDIR $PYSETUP_PATH
COPY poetry.lock pyproject.toml README.md .
# Copy ctms folder for ctms-cli installation.
COPY ctms /opt/pysetup/ctms/
RUN $POETRY_HOME/bin/poetry install --only main

FROM python:3.12.7-slim AS production

COPY bin/update_and_install_system_packages.sh /opt
RUN opt/update_and_install_system_packages.sh libpq5

ENV PATH="/opt/pysetup/.venv/bin:$PATH" \
    PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    VENV_PATH="/opt/pysetup/.venv"

COPY --from=python-base $VENV_PATH $VENV_PATH

# Set up user and group
ARG userid=10001
ARG groupid=10001
RUN groupadd --gid $groupid app && \
    useradd -g app --uid $userid --shell /usr/sbin/nologin --create-home app
USER app
WORKDIR /app

# Copy only what is necessary to reduce image size and security risks
# FILES
COPY --chown=app:app \
    alembic.ini \
    asgi.py \
    pyproject.toml \
    version.json \
    /app/
# DIRECTORIES
COPY --chown=app:app bin /app/bin
COPY --chown=app:app ctms /app/ctms
COPY --chown=app:app migrations /app/migrations
COPY --chown=app:app suppression-list /app/suppression-list

EXPOSE $PORT
CMD ["python", "asgi.py"]
