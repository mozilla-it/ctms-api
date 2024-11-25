FROM python:3.13.0 AS python-base

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=off \
    POETRY_HOME=/opt/poetry\
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PYSETUP_PATH="/opt/pysetup"

RUN python3 -m venv $POETRY_HOME && \
    $POETRY_HOME/bin/pip install poetry==1.7.1 && \
    $POETRY_HOME/bin/poetry --version

WORKDIR $PYSETUP_PATH
COPY ./poetry.lock ./pyproject.toml ./
RUN $POETRY_HOME/bin/poetry install --no-root --only main

FROM python:3.13.0-slim AS production

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

COPY --chown=app:app . .

EXPOSE $PORT
CMD ["python", "asgi.py"]
