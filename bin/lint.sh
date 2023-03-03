#!/bin/sh

set -e

POETRY_RUN="poetry run"
CURRENT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASE_DIR="$(dirname "$CURRENT_DIR")"
HAS_GIT="$(command -v git || echo '')"
echo $HAS_GIT

bandit () {
  $POETRY_RUN bandit -lll --recursive "${BASE_DIR}" --exclude "${BASE_DIR}/poetry.lock,${BASE_DIR}/.venv,${BASE_DIR}/.mypy,${BASE_DIR}/build"
}
black () {
  $POETRY_RUN black ${check:+--check} "${BASE_DIR}"
}
detect_secrets () {
  if [ -n "$HAS_GIT" ]; then
    # Scan only files fixed into the repo, omit poetry.lock
    FILES_TO_SCAN=`git ls-tree --full-tree -r --name-only HEAD | grep -v poetry.lock`
    $POETRY_RUN detect-secrets-hook $FILES_TO_SCAN --baseline .secrets.baseline
  else
    echo "Git not available. Skip detect-secrets"
  fi
}
isort () {
  $POETRY_RUN isort ${check:+--check-only} "${BASE_DIR}"
}
pylint () {
  $POETRY_RUN pylint "${BASE_DIR}/ctms" "${BASE_DIR}/tests/unit"
}
mypy () {
  $POETRY_RUN mypy "${BASE_DIR}/ctms"
}
all () {
  echo "running black"
  black
  echo "running isort"
  isort
  echo "running mypy"
  mypy
  echo "running pylint"
  pylint
  echo "running bandit"
  bandit
  echo "running detect_secrets"
  detect_secrets
}

usage () {
  echo "Usage: bin/lint.sh [OPTION]"
  echo " run linting checks"
  echo "Options":
  echo "  bandit"
  echo "  black [--fix]"
  echo "  detect-secrets"
  echo "  isort [--fix]"
  echo "  mypy"
  echo "  pylint"
  echo "  yamllint"
}

subcommand='';
check="true"
if [ -z $1 ]; then
  all
else
  subcommand=$1; shift
  case $subcommand in
    "black" | "isort")
      case $1 in
        "--fix")
          check=""
        ;;
      esac
      case $subcommand in
        "isort") isort;;
        "black") black;;
      esac
    ;;

    "pylint") pylint;;
    "mypy") mypy;;
    "bandit") bandit;;
    "detect-secrets") detect_secrets;;
    *) usage;;
  esac
fi
